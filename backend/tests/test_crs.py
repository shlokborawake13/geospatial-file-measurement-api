"""Tests for CRSService."""
import math

import geopandas as gpd
import pytest
from pyproj import CRS
from shapely.geometry import Point, Polygon

from app.core.exceptions import InvalidCRSError
from app.services.crs_service import CRSService

service = CRSService()


def _gdf(geom, epsg: int) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame([{"geometry": geom}], crs=f"EPSG:{epsg}")


class TestIsGeographic:
    def test_epsg4326_is_geographic(self):
        assert service.is_geographic(CRS.from_epsg(4326)) is True

    def test_epsg3857_is_not_geographic(self):
        assert service.is_geographic(CRS.from_epsg(3857)) is False

    def test_utm_is_not_geographic(self):
        assert service.is_geographic(CRS.from_epsg(32643)) is False


class TestNormalizeCRS:
    def test_epsg4326_string(self):
        assert service.normalize_crs_string(CRS.from_epsg(4326)) == "EPSG:4326"

    def test_epsg32643_string(self):
        assert service.normalize_crs_string(CRS.from_epsg(32643)) == "EPSG:32643"


class TestUTMSelection:
    def _utm_for_point(self, lon: float, lat: float) -> str:
        pt = Point(lon, lat)
        gdf = _gdf(pt, 4326)
        _, epsg_str = service.select_measurement_crs(gdf)
        return epsg_str

    def test_northern_hemisphere_india(self):
        # Maharashtra, India ≈ lon=75, lat=19 → zone 43 north → EPSG:32643
        epsg = self._utm_for_point(75.0, 19.0)
        zone = math.floor((75.0 + 180.0) / 6.0) + 1
        assert epsg == f"EPSG:326{zone:02d}"

    def test_southern_hemisphere_australia(self):
        # Sydney ≈ lon=151, lat=-34 → zone 56 south → EPSG:32756
        epsg = self._utm_for_point(151.0, -34.0)
        zone = math.floor((151.0 + 180.0) / 6.0) + 1
        assert epsg == f"EPSG:327{zone:02d}"

    def test_northern_hemisphere_london(self):
        # London ≈ lon=-0.1, lat=51.5 → zone 30 north → EPSG:32630
        epsg = self._utm_for_point(-0.1, 51.5)
        zone = math.floor((-0.1 + 180.0) / 6.0) + 1
        assert epsg == f"EPSG:326{zone:02d}"

    def test_northern_hemisphere_new_york(self):
        # New York ≈ lon=-74, lat=40.7 → zone 18 north → EPSG:32618
        epsg = self._utm_for_point(-74.0, 40.7)
        zone = math.floor((-74.0 + 180.0) / 6.0) + 1
        assert epsg == f"EPSG:326{zone:02d}"


class TestProjectedCRS:
    def test_projected_crs_used_directly(self):
        poly = Polygon([(0, 0), (1000, 0), (1000, 1000), (0, 1000), (0, 0)])
        gdf = _gdf(poly, 32643)
        _, epsg_str = service.select_measurement_crs(gdf)
        assert epsg_str == "EPSG:32643"


class TestMissingCRS:
    def test_missing_crs_raises(self):
        pt = Point(0, 0)
        gdf = gpd.GeoDataFrame([{"geometry": pt}])  # no CRS
        with pytest.raises(InvalidCRSError):
            service.select_measurement_crs(gdf)
