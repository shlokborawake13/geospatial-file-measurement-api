"""
Repository for the `measurements` table.
"""
import logging
from typing import List, Tuple
from app.models.measurement import Measurement, MeasurementStatus, MeasurementType
from app.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class MeasurementRepository:
    def __init__(self):
        self._db = get_supabase_client()

    def bulk_insert(self, measurements: List[Measurement]) -> None:
        if not measurements:
            return
        rows = [self._to_row(m) for m in measurements]
        try:
            self._db.table("measurements").insert(rows).execute()
        except Exception as exc:
            from app.core.exceptions import DatabaseError
            logger.error("[DATABASE] measurements.bulk_insert failed: %s", exc)
            raise DatabaseError("Database operation 'measurements.bulk_insert' failed.") from exc
        logger.debug("[DATABASE] Inserted %d measurements", len(measurements))

    def get_paginated_by_file(
        self, file_id: str, page: int, page_size: int
    ) -> Tuple[List[dict], int]:
        offset = (page - 1) * page_size
        try:
            count_resp = (
                self._db.table("measurements")
                .select("features!inner(file_id)", count="exact")
                .eq("features.file_id", file_id)
                .execute()
            )
            total = count_resp.count or 0

            data_resp = (
                self._db.table("measurements")
                .select(
                    "id, feature_id, measurement_type, value, unit, measurement_crs, status, error_message, "
                    "features!inner(feature_index, geometry_type, file_id)"
                )
                .eq("features.file_id", file_id)
                .order("features(feature_index)")
                .range(offset, offset + page_size - 1)
                .execute()
            )
        except Exception as exc:
            from app.core.exceptions import DatabaseError
            logger.error("[DATABASE] measurements.get_paginated_by_file failed: %s", exc)
            raise DatabaseError("Database operation 'measurements.get_paginated_by_file' failed.") from exc

        return data_resp.data or [], total

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _to_row(m: Measurement) -> dict:
        return {
            "id": m.id,
            "feature_id": m.feature_id,
            "measurement_type": m.measurement_type.value if m.measurement_type else None,
            "value": m.value,
            "unit": m.unit,
            "measurement_crs": m.measurement_crs,
            "status": m.status.value,
            "error_message": m.error_message,
            "created_at": m.created_at.isoformat(),
        }
