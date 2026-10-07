"""Tests for ShapefileProcessor."""
import io
import zipfile

import pytest

from app.core.exceptions import (
    InvalidShapefileError,
    MissingShapefileComponentError,
    InvalidCRSError,
)
from app.services.shapefile_processor import ShapefileProcessor

processor = ShapefileProcessor()


def test_invalid_zip_raises(invalid_zip_bytes):
    with pytest.raises(InvalidShapefileError):
        processor.process(invalid_zip_bytes)


def test_zip_missing_shp_raises(zip_missing_shp_bytes):
    with pytest.raises(MissingShapefileComponentError):
        processor.process(zip_missing_shp_bytes)


def test_zip_missing_dbf_raises(zip_missing_dbf_bytes):
    with pytest.raises(MissingShapefileComponentError):
        processor.process(zip_missing_dbf_bytes)


def test_zip_missing_shx_raises(zip_missing_shx_bytes):
    with pytest.raises(MissingShapefileComponentError):
        processor.process(zip_missing_shx_bytes)


def test_valid_shapefile_returns_geodataframe(valid_zip_bytes):
    gdf = processor.process(valid_zip_bytes)
    assert len(gdf) > 0
    assert gdf.crs is not None


def test_valid_shapefile_crs_detected(valid_zip_bytes):
    gdf = processor.process(valid_zip_bytes)
    assert gdf.crs.to_epsg() is not None


def test_zip_slip_prevention():
    """A ZIP with a path traversal member must be rejected."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../../etc/passwd", "root:x:0:0")
        zf.writestr("data.shp", b"\x00" * 10)
        zf.writestr("data.shx", b"\x00" * 10)
        zf.writestr("data.dbf", b"\x00" * 10)
    with pytest.raises(InvalidShapefileError, match="Unsafe path"):
        processor.process(buf.getvalue())
