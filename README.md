# Geospatial File Measurement API

A production-quality web application for uploading KML and Shapefile data, extracting geospatial features, and calculating CRS-correct metric measurements (area in m², length in m).

---

## Problem

Geospatial files store coordinates in a variety of Coordinate Reference Systems (CRS). The most common — **EPSG:4326 (WGS84)** — uses angular units (degrees of latitude/longitude). Calculating area or length directly on degree-based coordinates produces meaningless results.

This system always reprojects geographic data into an appropriate **projected metric CRS** (UTM) before any measurement is performed.

---

## Features

- Upload `.kml` or `.zip` Shapefile archives
- Secure ZIP extraction (Zip Slip prevention, size/count limits)
- Feature extraction with geometry type detection
- CRS detection and automatic UTM zone selection
- Polygon → area (m²), LineString → length (m), Point → no measurement
- MultiPolygon and MultiLineString support
- Invalid geometry repair via Shapely `make_valid()`
- Per-feature failure isolation (one bad feature does not fail the file)
- Supabase PostgreSQL persistence (JSONB geometry storage, no PostGIS)
- Supabase Storage for original file uploads
- Paginated measurements API (max 500 per page)
- React + TypeScript frontend with drag-and-drop upload
- Full test suite with numeric measurement assertions
- Docker support

---

## Architecture

```
React (Vite + TypeScript)
        ↓
FastAPI (Python 3.12)
        ↓
Service Layer
  ├── FileValidator
  ├── KMLProcessor / ShapefileProcessor
  ├── GeospatialProcessor (common pipeline)
  ├── CRSService (UTM selection + reprojection)
  ├── GeometryService (validation, repair, GeoJSON)
  └── MeasurementService (area / length)
        ↓
Repository Layer
  ├── FileRepository
  ├── FeatureRepository
  └── MeasurementRepository
        ↓
Supabase PostgreSQL (JSONB)  +  Supabase Storage
```

---

## File Processing Pipeline

```
Upload
  → Validate (extension, size, content integrity)
  → Create file record (status: UPLOADED)
  → Store original file in Supabase Storage
  → Update status: PROCESSING
  → Parse into GeoDataFrame (KML or Shapefile)
  → Detect source CRS
  → Select measurement CRS (UTM or existing projected CRS)
  → For each feature:
      → Validate / repair geometry
      → Reproject to measurement CRS
      → Calculate measurement
      → Build Feature + Measurement domain objects
  → Bulk insert features
  → Bulk insert measurements
  → Update status: COMPLETED
```

On any unrecoverable error → status: FAILED with error message saved.

---

## CRS Strategy

### Geographic CRS (e.g. EPSG:4326)

Coordinates are in degrees. **Never** call `.area` or `.length` on these.

The system calculates the centroid of the dataset's bounding box, determines the UTM zone:

```
zone = floor((longitude + 180) / 6) + 1
Northern hemisphere → EPSG:326XX
Southern hemisphere → EPSG:327XX
```

All geometries are reprojected into this UTM CRS before measurement.

### Projected CRS (e.g. EPSG:27700, EPSG:32643)

Used directly for measurement — no reprojection needed.

### Missing CRS

Returns `INVALID_CRS` error. CRS is required for reliable measurement.

### Limitation — Multi-zone datasets

For V1, one representative UTM zone is selected for the entire dataset. Datasets spanning multiple UTM zones will have minor distortion at the edges. Future improvement: per-feature UTM selection or geodesic measurement.

---

## Database Schema

### files
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| filename | TEXT | |
| file_type | TEXT | KML / SHP_ZIP |
| storage_path | TEXT | Supabase Storage path |
| original_crs | TEXT | e.g. EPSG:4326 |
| feature_count | INTEGER | |
| status | TEXT | UPLOADED / PROCESSING / COMPLETED / FAILED |
| error_message | TEXT | |
| processing_duration_ms | INTEGER | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### features
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| file_id | UUID FK → files.id | CASCADE DELETE |
| feature_index | INTEGER | |
| geometry_type | TEXT | Polygon / LineString / Point / … |
| geometry | JSONB | GeoJSON |
| properties | JSONB | Source attributes |
| original_crs | TEXT | |
| created_at | TIMESTAMPTZ | |

### measurements
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| feature_id | UUID FK → features.id | CASCADE DELETE |
| measurement_type | TEXT | AREA / LENGTH / null |
| value | NUMERIC | |
| unit | TEXT | m² / m |
| measurement_crs | TEXT | e.g. EPSG:32643 |
| status | TEXT | SUCCESS / NOT_REQUIRED / UNSUPPORTED / FAILED |
| error_message | TEXT | |
| created_at | TIMESTAMPTZ | |

### SQL to create tables and indexes

```sql
CREATE TABLE files (
    id UUID PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    original_crs TEXT,
    feature_count INTEGER,
    status TEXT NOT NULL,
    error_message TEXT,
    processing_duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE features (
    id UUID PRIMARY KEY,
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    feature_index INTEGER NOT NULL,
    geometry_type TEXT NOT NULL,
    geometry JSONB,
    properties JSONB,
    original_crs TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(file_id, feature_index)
);

CREATE TABLE measurements (
    id UUID PRIMARY KEY,
    feature_id UUID NOT NULL REFERENCES features(id) ON DELETE CASCADE,
    measurement_type TEXT,
    value NUMERIC,
    unit TEXT,
    measurement_crs TEXT,
    status TEXT NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_features_file_id ON features(file_id);
CREATE INDEX idx_measurements_feature_id ON measurements(feature_id);
CREATE INDEX idx_files_status ON files(status);
```

---

## API Documentation

Interactive docs available at `/docs` and `/redoc` when the server is running.

### POST /api/files/
Upload a KML or Shapefile ZIP.

```bash
curl -X POST \
  -F "file=@sample_data/kml/polygon.kml" \
  http://localhost:8000/api/files/
```

Response (201):
```json
{
  "id": "uuid",
  "filename": "polygon.kml",
  "file_type": "KML",
  "feature_count": 1,
  "crs": "EPSG:4326",
  "status": "COMPLETED"
}
```

### GET /api/files/{id}/
```bash
curl http://localhost:8000/api/files/{id}/
```

### GET /api/files/{id}/measurements/
```bash
curl "http://localhost:8000/api/files/{id}/measurements/?page=1&page_size=100"
```

### GET /health
```bash
curl http://localhost:8000/health/
# {"status": "ok"}
```

---

## Local Setup

```bash
git clone https://github.com/your-org/geospatial-measurement-api.git
cd geospatial-measurement-api
```

### Backend

```bash
cd backend
python -m venv .venv
```

Activate (Windows):
```powershell
.\.venv\Scripts\Activate.ps1
```

Activate (macOS/Linux):
```bash
source .venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Configure environment:
```bash
cp .env.example .env
# Edit .env and fill in SUPABASE_URL and SUPABASE_KEY
```

Run the server:
```bash
python -m uvicorn app.main:app --reload
```

API available at: http://localhost:8000
Docs at: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend available at: http://localhost:5173

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | required |
| `SUPABASE_KEY` | Supabase anon or service role key | required |
| `SUPABASE_STORAGE_BUCKET` | Storage bucket name | `geospatial-files` |
| `MAX_UPLOAD_SIZE_MB` | Maximum upload size | `50` |
| `TEMP_DIR` | Temporary extraction directory | `/tmp/geospatial-processing` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:5173` |
| `ENVIRONMENT` | `development` or `production` | `development` |

---

## Docker

```bash
# Build and start both services
docker-compose up --build

# Backend only
docker-compose up backend
```

Requires a `.env` file in `backend/` with Supabase credentials.

---

## Testing

```bash
cd backend
pytest tests/ -v
```

Tests cover:
- File validation (extension, size, content, ZIP structure)
- KML parsing (polygon, linestring, point, mixed, invalid)
- Shapefile processing (valid, invalid, missing components, Zip Slip)
- CRS service (UTM zone selection, geographic vs projected, hemispheres)
- Measurements (actual numeric values, not just status codes)
- Full pipeline integration
- API endpoints (upload, get file, get measurements, pagination, errors)

---

## Design Decisions

| Decision | Reason |
|----------|--------|
| FastAPI | Async-ready, automatic OpenAPI docs, Pydantic validation |
| GeoPandas | Industry-standard Python GIS stack; handles KML + Shapefile uniformly |
| Supabase | Managed PostgreSQL + Storage without infrastructure overhead |
| JSONB geometry | Avoids PostGIS dependency; GeoJSON is portable and queryable |
| No PostGIS (V1) | Keeps the stack simple; JSONB is sufficient for storage and retrieval |
| UTM CRS selection | Automatic, data-driven; no hardcoded EPSG codes |
| Synchronous processing | Sufficient for V1; service layer is structured for easy async/worker migration |
| Per-feature failure isolation | One bad geometry should not invalidate an entire file |

---

## Limitations

- Multi-zone datasets use one representative UTM zone (minor edge distortion)
- Files with missing CRS are rejected (cannot safely measure without CRS)
- Synchronous processing (large files block the request)
- No authentication on API endpoints
- GeometryCollection type is classified as unsupported

---

## Future Improvements

- Background processing with Celery/Redis for large files
- Geodesic measurement using `pyproj.Geod` for highest accuracy
- Per-feature UTM zone selection
- PostGIS for spatial querying and indexing
- GeoJSON upload support
- Authentication (API keys or JWT)
- Streaming upload for very large files
- Cloud deployment (AWS ECS / GCP Cloud Run)
- Spatial querying (find features within a bounding box)
