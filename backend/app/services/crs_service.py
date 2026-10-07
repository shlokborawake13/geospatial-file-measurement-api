"""
CRS Service
===========

Responsible for:
- Detecting whether a CRS is geographic or projected.
- Selecting an appropriate projected CRS for metric measurement.
- Reprojecting geometries.

CRS Selection Strategy
----------------------
If the source CRS is already projected (e.g. EPSG:27700, EPSG:32643) it is
used directly for measurement.

If the source CRS is geographic (e.g. EPSG:4326) the system selects the
appropriate UTM zone based on the centroid of the dataset:

    zone = floor((longitude + 180) / 6) + 1

    Northern hemisphere → EPSG:326XX
    Southern hemisphere → EPSG:327XX

This is a representative-point strategy: one UTM zone is chosen for the
entire dataset.  For datasets that span multiple UTM zones this introduces
a small distortion at the edges.  This is documented as a V1 limitation.

IMPORTANT: Never call geometry.area or geometry.length on EPSG:4326
coordinates — that produces values in degrees, not metres.
"""
import math
import logging
from typing import Optional, Tuple

import geopandas as gpd
from pyproj import CRS, Transformer
import shapely
from shapely.geometry.base import BaseGeometry

logger = logging.getLogger(__name__)


class CRSService:
    # ── Public API ────────────────────────────────────────────────────────────

    def normalize_crs_string(self, crs: CRS) -> str:
        """Return a canonical EPSG string, e.g. 'EPSG:4326'."""
        epsg = crs.to_epsg()
        if epsg:
            return f"EPSG:{epsg}"
        return crs.to_string()

    def is_geographic(self, crs: CRS) -> bool:
        """Return True if the CRS uses angular (degree) units."""
        return crs.is_geographic

    def select_measurement_crs(self, gdf: gpd.GeoDataFrame) -> Tuple[CRS, str]:
        """
        Choose the best projected CRS for metric measurement.

        Returns (pyproj.CRS, epsg_string).

        Raises InvalidCRSError if no usable CRS can be determined.
        """
        from app.core.exceptions import InvalidCRSError

        if gdf.crs is None:
            raise InvalidCRSError(
                "The file has no CRS information. "
                "A valid CRS is required for reliable metric measurement."
            )

        source_crs = gdf.crs

        if not self.is_geographic(source_crs):
            # Already projected — use as-is
            epsg_str = self.normalize_crs_string(source_crs)
            logger.info("Source CRS is projected, using %s for measurement", epsg_str)
            return source_crs, epsg_str

        # Geographic CRS — select UTM zone from dataset centroid
        utm_crs, epsg_str = self._utm_crs_from_gdf(gdf)
        logger.info(
            "Source CRS is geographic (%s), selected UTM %s for measurement",
            self.normalize_crs_string(source_crs),
            epsg_str,
        )
        return utm_crs, epsg_str

    def reproject_geometry(
        self, geometry: BaseGeometry, from_crs: CRS, to_crs: CRS
    ) -> BaseGeometry:
        """Reproject a single Shapely geometry between two CRS."""
        transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)

        def _transform(coords):
            # coords shape: (N, 2) — split into x/y arrays, transform, re-stack
            import numpy as np
            xs, ys = transformer.transform(coords[:, 0], coords[:, 1])
            return np.column_stack([xs, ys])

        return shapely.transform(geometry, _transform, include_z=False)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _utm_crs_from_gdf(self, gdf: gpd.GeoDataFrame) -> Tuple[CRS, str]:
        """Derive UTM CRS from the centroid of the dataset's bounding box."""
        # Reproject to WGS84 first to get reliable lon/lat centroid
        wgs84 = CRS.from_epsg(4326)
        if gdf.crs.to_epsg() != 4326:
            gdf_wgs84 = gdf.to_crs(wgs84)
        else:
            gdf_wgs84 = gdf

        total_bounds = gdf_wgs84.total_bounds  # (minx, miny, maxx, maxy)
        lon = (total_bounds[0] + total_bounds[2]) / 2.0
        lat = (total_bounds[1] + total_bounds[3]) / 2.0

        zone = math.floor((lon + 180.0) / 6.0) + 1
        zone = max(1, min(60, zone))  # clamp to valid range

        if lat >= 0:
            epsg_code = 32600 + zone   # Northern hemisphere
        else:
            epsg_code = 32700 + zone   # Southern hemisphere

        epsg_str = f"EPSG:{epsg_code}"
        logger.debug(
            "UTM selection: lon=%.4f lat=%.4f → zone=%d → %s",
            lon, lat, zone, epsg_str,
        )
        return CRS.from_epsg(epsg_code), epsg_str
