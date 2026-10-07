"""
Repository for the `features` table.
"""
import json
import logging
from typing import List
from app.models.feature import Feature
from app.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class FeatureRepository:
    def __init__(self):
        self._db = get_supabase_client()

    def bulk_insert(self, features: List[Feature]) -> None:
        """Insert all features for a file in a single request."""
        if not features:
            return
        rows = [self._to_row(f) for f in features]
        try:
            self._db.table("features").insert(rows).execute()
        except Exception as exc:
            from app.core.exceptions import DatabaseError
            logger.error("[DATABASE] features.bulk_insert failed: %s", exc)
            raise DatabaseError("Database operation 'features.bulk_insert' failed.") from exc
        logger.debug("[DATABASE] Inserted %d features for file_id=%s", len(features), features[0].file_id)

    def get_by_file(self, file_id: str) -> List[Feature]:
        response = (
            self._db.table("features")
            .select("*")
            .eq("file_id", file_id)
            .order("feature_index")
            .execute()
        )
        return [self._from_row(r) for r in (response.data or [])]

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _to_row(feature: Feature) -> dict:
        return {
            "id": feature.id,
            "file_id": feature.file_id,
            "feature_index": feature.feature_index,
            "geometry_type": feature.geometry_type,
            "geometry": feature.geometry,       # JSONB — pass dict directly
            "properties": feature.properties,   # JSONB — pass dict directly
            "original_crs": feature.original_crs,
            "created_at": feature.created_at.isoformat(),
        }

    @staticmethod
    def _from_row(row: dict) -> Feature:
        from datetime import datetime
        return Feature(
            id=row["id"],
            file_id=row["file_id"],
            feature_index=row["feature_index"],
            geometry_type=row["geometry_type"],
            geometry=row.get("geometry"),
            properties=row.get("properties"),
            original_crs=row.get("original_crs"),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
