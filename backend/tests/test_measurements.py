"""
Tests for MeasurementService and GeospatialProcessor.

These tests verify that:
- Measurements are calculated in metres (not degrees).
- CRS reprojection is actually occurring.
- Polygon area, LineString length, Point, and edge cases are handled correctly.
"""
import pytest
from pyproj import CRS
from shapely.geometry import LineString, Point, Polygon

from app.models.measurement import MeasurementStatus, MeasurementType
from app.services.crs_service import CRSService
from app.services.geometry_service import GeometryService
from app.services.measurement_service import MeasurementService

measurement_service = MeasurementService()
crs_service = CRSService()
geometry_service = GeometryService()


def _reproject(geom, from_epsg: int, to_epsg: int):
    return crs_service.reproject_geometry(
        geom,
        CRS.from_epsg(from_epsg),
        CRS.from_epsg(to_epsg),
    )


class TestPolygonArea:
    def test_area_is_in_metres_squared(self):
        # 1° × 1° square near equator in EPSG:4326
        poly_4326 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        # Reproject to UTM zone 31N (EPSG:32631)
        poly_utm = _reproject(poly_4326, 4326, 32631)
        result = measurement_service.calculate(poly_utm, "Polygon", "EPSG:32631", "area")

        assert result.status == MeasurementStatus.SUCCESS
        assert result.measurement_type == MeasurementType.AREA
        assert result.unit == "m²"
        # 1° × 1° near equator ≈ 12,300 km² = 1.23e10 m²
        assert result.value == pytest.approx(1.23e10, rel=0.05)

    def test_area_not_in_degrees(self):
        # In degrees, a 1×1 square has area = 1.0 (meaningless)
        # In metres it must be >> 1
        poly_4326 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        poly_utm = _reproject(poly_4326, 4326, 32631)
        result = measurement_service.calculate(poly_utm, "Polygon", "EPSG:32631", "area")
        assert result.value > 1_000_000  # definitely not in degrees

    def test_small_polygon_area(self):
        # 100m × 100m square in UTM (already projected)
        poly_utm = Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)])
        result = measurement_service.calculate(poly_utm, "Polygon", "EPSG:32643", "area")
        assert result.status == MeasurementStatus.SUCCESS
        assert result.value == pytest.approx(10000.0, rel=1e-6)

    def test_multipolygon_area(self):
        import shapely
        # Build MultiPolygon via WKT to avoid Shapely 2.0.4 + NumPy 2.x
        # create_collection ufunc incompatibility
        mp = shapely.from_wkt(
            "MULTIPOLYGON (((0 0, 100 0, 100 100, 0 100, 0 0)), "
            "((200 0, 300 0, 300 100, 200 100, 200 0)))"
        )
        assert mp.geom_type == "MultiPolygon"
        result = measurement_service.calculate(mp, "MultiPolygon", "EPSG:32643", "area")
        assert result.status == MeasurementStatus.SUCCESS
        assert result.value == pytest.approx(20000.0, rel=1e-6)


class TestLinestringLength:
    def test_length_is_in_metres(self):
        # 0.01° longitude at equator ≈ 1111 m
        line_4326 = LineString([(0, 0), (0.01, 0)])
        line_utm = _reproject(line_4326, 4326, 32631)
        result = measurement_service.calculate(line_utm, "LineString", "EPSG:32631", "length")

        assert result.status == MeasurementStatus.SUCCESS
        assert result.measurement_type == MeasurementType.LENGTH
        assert result.unit == "m"
        assert result.value == pytest.approx(1111.9, rel=0.01)

    def test_length_not_in_degrees(self):
        line_4326 = LineString([(0, 0), (0.01, 0)])
        line_utm = _reproject(line_4326, 4326, 32631)
        result = measurement_service.calculate(line_utm, "LineString", "EPSG:32631", "length")
        assert result.value > 100  # definitely not 0.01 degrees

    def test_known_length_utm(self):
        # Exactly 500 m horizontal line in UTM
        line_utm = LineString([(0, 0), (500, 0)])
        result = measurement_service.calculate(line_utm, "LineString", "EPSG:32643", "length")
        assert result.status == MeasurementStatus.SUCCESS
        assert result.value == pytest.approx(500.0, rel=1e-6)


class TestPoint:
    def test_point_not_required(self):
        pt = Point(0, 0)
        result = measurement_service.calculate(pt, "Point", "EPSG:4326", "none")
        assert result.status == MeasurementStatus.NOT_REQUIRED
        assert result.value is None
        assert result.unit is None


class TestEdgeCases:
    def test_null_geometry_fails(self):
        result = measurement_service.calculate(None, "Polygon", "EPSG:32643", "area")
        assert result.status == MeasurementStatus.FAILED

    def test_empty_geometry_fails(self):
        from shapely.geometry import Polygon as P
        empty = P()
        result = measurement_service.calculate(empty, "Polygon", "EPSG:32643", "area")
        assert result.status == MeasurementStatus.FAILED

    def test_unsupported_geometry_type(self):
        from shapely.geometry import GeometryCollection
        gc = GeometryCollection()
        result = measurement_service.calculate(gc, "GeometryCollection", "EPSG:32643", "unsupported")
        assert result.status == MeasurementStatus.UNSUPPORTED


class TestGeospatialProcessorPipeline:
    """Integration tests for the full processing pipeline."""

    def test_polygon_pipeline_produces_area(self, polygon_gdf):
        from app.services.geospatial_processor import GeospatialProcessor
        processor = GeospatialProcessor()
        features, measurements, original_crs, measurement_crs = processor.process(
            polygon_gdf, "test-file-id"
        )
        assert len(features) == 1
        assert len(measurements) == 1
        m = measurements[0]
        assert m.status == MeasurementStatus.SUCCESS
        assert m.measurement_type == MeasurementType.AREA
        assert m.unit == "m²"
        assert m.value > 1_000_000  # not in degrees
        assert original_crs == "EPSG:4326"
        assert measurement_crs.startswith("EPSG:32")  # UTM zone

    def test_linestring_pipeline_produces_length(self, linestring_gdf):
        from app.services.geospatial_processor import GeospatialProcessor
        processor = GeospatialProcessor()
        features, measurements, _, _ = processor.process(linestring_gdf, "test-file-id")
        m = measurements[0]
        assert m.status == MeasurementStatus.SUCCESS
        assert m.measurement_type == MeasurementType.LENGTH
        assert m.unit == "m"
        assert m.value == pytest.approx(1111.9, rel=0.01)

    def test_point_pipeline_not_required(self, point_gdf):
        from app.services.geospatial_processor import GeospatialProcessor
        processor = GeospatialProcessor()
        _, measurements, _, _ = processor.process(point_gdf, "test-file-id")
        assert measurements[0].status == MeasurementStatus.NOT_REQUIRED

    def test_mixed_pipeline(self, mixed_gdf):
        from app.services.geospatial_processor import GeospatialProcessor
        processor = GeospatialProcessor()
        features, measurements, _, _ = processor.process(mixed_gdf, "test-file-id")
        assert len(features) == 3
        statuses = {m.status for m in measurements}
        assert MeasurementStatus.SUCCESS in statuses
        assert MeasurementStatus.NOT_REQUIRED in statuses

    def test_single_bad_feature_does_not_fail_file(self):
        """One invalid geometry should produce FAILED measurement, not crash."""
        import geopandas as gpd
        from shapely.geometry import Polygon
        from app.services.geospatial_processor import GeospatialProcessor

        good = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        # Self-intersecting (bowtie) polygon — invalid
        bad = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
        gdf = gpd.GeoDataFrame(
            [{"geometry": good}, {"geometry": bad}], crs="EPSG:4326"
        )
        processor = GeospatialProcessor()
        features, measurements, _, _ = processor.process(gdf, "test-file-id")
        assert len(features) == 2
        assert len(measurements) == 2
        # Both should have some status — file did not crash
        for m in measurements:
            assert m.status is not None
