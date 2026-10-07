"""
Repository for the `files` table.

All database operations for file records are isolated here.
"""
import logging
from typing import Optional
from app.models.file import FileRecord, FileStatus
from app.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def _db_error(operation: str, exc: Exception) -> Exception:
    """Log the technical detail and return a sanitised DatabaseError."""
    from app.core.exceptions import DatabaseError
    logger.error("[DATABASE] %s failed: %s", operation, exc)
    return DatabaseError(f"Database operation '{operation}' failed.")


class FileRepository:
    def __init__(self):
        self._db = get_supabase_client()

    def insert(self, record: FileRecord) -> None:
        """Insert or upsert a new file record (safe against duplicate id retries)."""
        try:
            self._db.table("files").upsert(self._to_row(record)).execute()
        except Exception as exc:
            raise _db_error("files.insert", exc) from exc
        logger.debug("[DATABASE] Inserted/upserted file record id=%s", record.id)

    def update_status(
        self,
        file_id: str,
        status: FileStatus,
        *,
        error_message: Optional[str] = None,
        feature_count: Optional[int] = None,
        original_crs: Optional[str] = None,
        processing_duration_ms: Optional[int] = None,
    ) -> None:
        """Partial update — only the fields that change during processing."""
        from datetime import datetime, timezone
        payload: dict = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if error_message is not None:
            payload["error_message"] = error_message
        if feature_count is not None:
            payload["feature_count"] = feature_count
        if original_crs is not None:
            payload["original_crs"] = original_crs
        if processing_duration_ms is not None:
            payload["processing_duration_ms"] = processing_duration_ms

        try:
            self._db.table("files").update(payload).eq("id", file_id).execute()
        except Exception as exc:
            raise _db_error("files.update_status", exc) from exc
        logger.debug("[DATABASE] Updated file id=%s status=%s", file_id, status.value)

    def get(self, file_id: str) -> Optional[FileRecord]:
        """Fetch a single file record by primary key."""
        try:
            response = (
                self._db.table("files").select("*").eq("id", file_id).maybe_single().execute()
            )
        except Exception as exc:
            raise _db_error("files.get", exc) from exc
        if response.data is None:
            return None
        return self._from_row(response.data)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _to_row(record: FileRecord) -> dict:
        return {
            "id": record.id,
            "filename": record.filename,
            "file_type": record.file_type.value,
            "storage_path": record.storage_path,
            "status": record.status.value,
            "original_crs": record.original_crs,
            "feature_count": record.feature_count,
            "error_message": record.error_message,
            "processing_duration_ms": record.processing_duration_ms,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
        }

    @staticmethod
    def _from_row(row: dict) -> FileRecord:
        from datetime import datetime
        return FileRecord(
            id=row["id"],
            filename=row["filename"],
            file_type=row["file_type"],
            storage_path=row["storage_path"],
            status=FileStatus(row["status"]),
            original_crs=row.get("original_crs"),
            feature_count=row.get("feature_count"),
            error_message=row.get("error_message"),
            processing_duration_ms=row.get("processing_duration_ms"),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
