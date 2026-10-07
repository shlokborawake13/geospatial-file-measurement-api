"""Generate sample_data/shapefile/valid.zip and invalid.zip."""
import geopandas as gpd
import io
import os
import shutil
import tempfile
import zipfile
from shapely.geometry import LineString, Point, Polygon

OUT_DIR = os.path.join(os.path.dirname(__file__), "sample_data", "shapefile")
os.makedirs(OUT_DIR, exist_ok=True)

# ── valid.zip — polygon-only shapefile (shapefiles require uniform geometry) ──
tmp = tempfile.mkdtemp()
gdf = gpd.GeoDataFrame(
    [
        {"name": "Polygon A", "area_km2": 12300, "geometry": Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])},
        {"name": "Polygon B", "area_km2": 6150,  "geometry": Polygon([(2, 0), (3, 0), (3, 1), (2, 1), (2, 0)])},
        {"name": "Polygon C", "area_km2": 3075,  "geometry": Polygon([(4, 0), (4.5, 0), (4.5, 0.5), (4, 0.5), (4, 0)])},
    ],
    crs="EPSG:4326",
)
gdf.to_file(os.path.join(tmp, "sample.shp"))

valid_path = os.path.join(OUT_DIR, "valid.zip")
with zipfile.ZipFile(valid_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for f in os.listdir(tmp):
        zf.write(os.path.join(tmp, f), f)
shutil.rmtree(tmp)
print(f"Created {valid_path} ({os.path.getsize(valid_path)} bytes)")

# ── invalid.zip ───────────────────────────────────────────────────────────────
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as zf:
    zf.writestr("README.txt", "Intentionally invalid — no shapefile components.")
invalid_path = os.path.join(OUT_DIR, "invalid.zip")
with open(invalid_path, "wb") as f:
    f.write(buf.getvalue())
print(f"Created {invalid_path} ({os.path.getsize(invalid_path)} bytes)")
