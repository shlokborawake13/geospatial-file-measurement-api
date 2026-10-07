from typing import Any, Dict, Optional, Tuple

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry


def geojson_to_shapely(geojson: Dict[str, Any]) -> Optional[BaseGeometry]:
    """Convert a GeoJSON dict to a Shapely geometry. Returns None on failure."""
    try:
        return shape(geojson)
    except Exception:
        return None


def bounding_box(geometry: BaseGeometry) -> Tuple[float, float, float, float]:
    """Return (minx, miny, maxx, maxy) for a geometry."""
    return geometry.bounds
