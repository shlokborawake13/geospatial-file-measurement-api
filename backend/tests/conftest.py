"""
Shared pytest fixtures.
"""
import io
import os
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString, Point, Polygon

# ── Patch Supabase before importing the app ───────────────────────────────────
# Tests must not require a live Supabase connection.

@pytest.fixture(autouse=True)
def mock_supabase(monkeypatch):
    """Replace the Supabase client with a MagicMock for all tests."""
    mock_client = MagicMock()
    # Simulate .maybe_single().execute() returning None (not found)
    mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None
    # Simulate insert/upsert/update returning success
    mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    # Storage
    mock_client.storage.from_.return_value.upload.return_value = MagicMock()

    monkeypatch.setattr(
        "app.utils.supabase_client.get_supabase_client",
        lambda: mock_client,
    )
    monkeypatch.setattr(
        "app.utils.storage.get_supabase_client",
        lambda: mock_client,
        raising=False,
    )
    monkeypatch.setattr(
        "app.repositories.file_repository.get_supabase_client",
        lambda: mock_client,
        raising=False,
    )
    return mock_client


@pytest.fixture
def client(mock_supabase):
    from app.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


# ── Sample file content ───────────────────────────────────────────────────────

SAMPLE_DIR = Path(__file__).parent.parent.parent / "sample_data"


@pytest.fixture
def polygon_kml_bytes() -> bytes:
    path = SAMPLE_DIR / "kml" / "polygon.kml"
    return path.read_bytes()


@pytest.fixture
def lines_kml_bytes() -> bytes:
    path = SAMPLE_DIR / "kml" / "lines.kml"
    return path.read_bytes()


@pytest.fixture
def points_kml_bytes() -> bytes:
    path = SAMPLE_DIR / "kml" / "points.kml"
    return path.read_bytes()


@pytest.fixture
def mixed_kml_bytes() -> bytes:
    path = SAMPLE_DIR / "kml" / "mixed.kml"
    return path.read_bytes()


@pytest.fixture
def valid_zip_bytes() -> bytes:
    path = SAMPLE_DIR / "shapefile" / "valid.zip"
    return path.read_bytes()


@pytest.fixture
def invalid_zip_bytes() -> bytes:
    """A file that looks like a ZIP but is corrupt."""
    return b"PK\x03\x04" + b"\x00" * 20


@pytest.fixture
def zip_missing_shp_bytes() -> bytes:
    """A valid ZIP that contains no .shp file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("data.dbf", b"\x00" * 10)
        zf.writestr("data.shx", b"\x00" * 10)
    return buf.getvalue()


@pytest.fixture
def zip_missing_dbf_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("data.shp", b"\x00" * 10)
        zf.writestr("data.shx", b"\x00" * 10)
    return buf.getvalue()


@pytest.fixture
def zip_missing_shx_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("data.shp", b"\x00" * 10)
        zf.writestr("data.dbf", b"\x00" * 10)
    return buf.getvalue()


# ── GeoDataFrame fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def polygon_gdf() -> gpd.GeoDataFrame:
    """A simple square polygon in EPSG:4326 with known approximate area."""
    # 1° × 1° square near equator ≈ ~12,300 km²
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    return gpd.GeoDataFrame(
        [{"name": "test_polygon", "geometry": poly}],
        crs="EPSG:4326",
    )


@pytest.fixture
def linestring_gdf() -> gpd.GeoDataFrame:
    """A simple line in EPSG:4326."""
    line = LineString([(0, 0), (0.01, 0)])  # ~1.11 km
    return gpd.GeoDataFrame(
        [{"name": "test_line", "geometry": line}],
        crs="EPSG:4326",
    )


@pytest.fixture
def point_gdf() -> gpd.GeoDataFrame:
    pt = Point(0, 0)
    return gpd.GeoDataFrame(
        [{"name": "test_point", "geometry": pt}],
        crs="EPSG:4326",
    )


@pytest.fixture
def mixed_gdf() -> gpd.GeoDataFrame:
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    line = LineString([(0, 0), (0.01, 0)])
    pt = Point(0, 0)
    return gpd.GeoDataFrame(
        [
            {"name": "poly", "geometry": poly},
            {"name": "line", "geometry": line},
            {"name": "point", "geometry": pt},
        ],
        crs="EPSG:4326",
    )
