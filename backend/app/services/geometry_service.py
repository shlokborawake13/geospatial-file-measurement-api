"""
Geometry Service
================

Handles:
- Converting Shapely geometries to GeoJSON dicts.
- Validating and repairing geometries where safe.
- Normalising geometry type strings.
"""
import logging
from typing import Any, Dict, Optional, Tuple

from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

logger = logging.getLogger(__name__)

# Geometry types that support area measurement
AREA_TYPES = {"Polygon", "MultiPolygon"}
# Geometry types that support length measurement
LENGTH_TYPES = {"LineString", "MultiLineString"}
# Geometry types that require no measurement
NO_MEASURE_TYPES = {"Point", "MultiPoint"}


class GeometryService:
    def to_geojson(self, geometry: BaseGeometry) -> Dict[str, Any]:
        """Convert a Shapely geometry to a GeoJSON-compatible dict."""
        return dict(mapping(geometry))

    def validate_and_repair(
        self, geometry: BaseGeometry, feature_index: int
    ) -> Tuple[Optional[BaseGeometry], Optional[str]]:
        """
        Validate a geometry and attempt repair if invalid.

        Returns (geometry, warning_message).
        Returns (None, error_message) if the geometry cannot be used.
        """
        if geometry is None or geometry.is_empty:
            return None, "Geometry is null or empty."

        if not geometry.is_valid:
            repaired = make_valid(geometry)
            if repaired.is_empty:
                return None, "Geometry is invalid and could not be repaired."
            logger.warning(
                "Feature %d: invalid geometry repaired using make_valid()", feature_index
            )
            return repaired, None

        return geometry, None

    def classify(self, geometry_type: str) -> str:
        """
        Return 'area', 'length', 'none', or 'unsupported'.
        """
        if geometry_type in AREA_TYPES:
            return "area"
        if geometry_type in LENGTH_TYPES:
            return "length"
        if geometry_type in NO_MEASURE_TYPES:
            return "none"
        return "unsupported"
