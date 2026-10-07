"""
Measurement Service
===================

Calculates metric measurements from projected geometries.

IMPORTANT: This service always receives geometries that have already been
reprojected into a metric CRS by the geospatial processor.  It must never
receive EPSG:4326 geometries for area/length calculation.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from shapely.geometry.base import BaseGeometry

from app.models.measurement import MeasurementStatus, MeasurementType

logger = logging.getLogger(__name__)


@dataclass
class MeasurementResult:
    status: MeasurementStatus
    measurement_type: Optional[MeasurementType] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    measurement_crs: Optional[str] = None
    error_message: Optional[str] = None


class MeasurementService:
    def calculate(
        self,
        geometry: Optional[BaseGeometry],
        geometry_type: str,
        measurement_crs: str,
        classification: str,
    ) -> MeasurementResult:
        """
        Calculate a measurement for a single projected geometry.

        Parameters
        ----------
        geometry:
            Shapely geometry already reprojected into measurement_crs.
        geometry_type:
            Original geometry type string (e.g. 'Polygon').
        measurement_crs:
            EPSG string of the projected CRS used (e.g. 'EPSG:32643').
        classification:
            One of 'area', 'length', 'none', 'unsupported'.
        """
        if classification == "none":
            return MeasurementResult(status=MeasurementStatus.NOT_REQUIRED)

        if classification == "unsupported":
            return MeasurementResult(
                status=MeasurementStatus.UNSUPPORTED,
                error_message=f"Geometry type '{geometry_type}' is not supported for measurement.",
            )

        if geometry is None or geometry.is_empty:
            return MeasurementResult(
                status=MeasurementStatus.FAILED,
                error_message="Geometry is null or empty; measurement skipped.",
            )

        try:
            if classification == "area":
                return self._area(geometry, measurement_crs)
            if classification == "length":
                return self._length(geometry, measurement_crs)
        except Exception as exc:
            logger.exception("Measurement failed for geometry_type=%s: %s", geometry_type, exc)
            return MeasurementResult(
                status=MeasurementStatus.FAILED,
                error_message=str(exc),
            )

        return MeasurementResult(
            status=MeasurementStatus.UNSUPPORTED,
            error_message=f"Unhandled classification '{classification}'.",
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _area(geometry: BaseGeometry, crs: str) -> MeasurementResult:
        area = geometry.area  # metres² in a projected CRS
        return MeasurementResult(
            status=MeasurementStatus.SUCCESS,
            measurement_type=MeasurementType.AREA,
            value=round(area, 4),
            unit="m²",
            measurement_crs=crs,
        )

    @staticmethod
    def _length(geometry: BaseGeometry, crs: str) -> MeasurementResult:
        length = geometry.length  # metres in a projected CRS
        return MeasurementResult(
            status=MeasurementStatus.SUCCESS,
            measurement_type=MeasurementType.LENGTH,
            value=round(length, 4),
            unit="m",
            measurement_crs=crs,
        )
