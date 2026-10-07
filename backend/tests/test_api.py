"""
API integration tests.

Supabase is mocked via the conftest autouse fixture.
File processing services are also mocked to isolate HTTP layer tests.
"""
import io
import json
from unittest.mock import MagicMock, patch

import pytest


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestUploadEndpoint:
    VALID_KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <Polygon><outerBoundaryIs><LinearRing>
        <coordinates>0,0 1,0 1,1 0,1 0,0</coordinates>
      </LinearRing></outerBoundaryIs></Polygon>
    </Placemark>
  </Document>
</kml>"""

    def test_upload_unsupported_extension_returns_400(self, client):
        response = client.post(
            "/api/files/",
            files={"file": ("data.csv", b"col1,col2", "text/csv")},
        )
        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

    def test_upload_oversized_file_returns_413(self, client):
        big = b"x" * (51 * 1024 * 1024)
        # Wrap in XML so it passes extension check
        response = client.post(
            "/api/files/",
            files={"file": ("big.kml", big, "application/vnd.google-earth.kml+xml")},
        )
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "FILE_TOO_LARGE"

    def test_upload_invalid_kml_content_returns_400(self, client):
        response = client.post(
            "/api/files/",
            files={"file": ("bad.kml", b"not xml content", "application/vnd.google-earth.kml+xml")},
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_KML"

    def test_upload_valid_kml_returns_201(self, client):
        """Mock the full processing pipeline to return a completed record."""
        from app.models.file import FileRecord, FileStatus, FileType
        from datetime import datetime, timezone

        mock_record = FileRecord(
            id="test-uuid-1234",
            filename="polygon.kml",
            file_type=FileType.KML,
            storage_path="uploads/test-uuid-1234/original/polygon.kml",
            status=FileStatus.COMPLETED,
            original_crs="EPSG:4326",
            feature_count=1,
            processing_duration_ms=120,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch("app.services.file_service.FileService.process_upload", return_value=mock_record):
            response = client.post(
                "/api/files/",
                files={"file": ("polygon.kml", self.VALID_KML, "application/vnd.google-earth.kml+xml")},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["id"] == "test-uuid-1234"
        assert body["filename"] == "polygon.kml"
        assert body["file_type"] == "KML"
        assert body["status"] == "COMPLETED"
        assert body["feature_count"] == 1
        assert body["crs"] == "EPSG:4326"


class TestGetFileEndpoint:
    def test_get_nonexistent_file_returns_404(self, client):
        response = client.get("/api/files/nonexistent-id/")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "FILE_NOT_FOUND"

    def test_get_existing_file_returns_200(self, client):
        from app.models.file import FileRecord, FileStatus, FileType
        from datetime import datetime, timezone

        mock_record = FileRecord(
            id="abc-123",
            filename="survey.kml",
            file_type=FileType.KML,
            storage_path="uploads/abc-123/original/survey.kml",
            status=FileStatus.COMPLETED,
            original_crs="EPSG:4326",
            feature_count=5,
            processing_duration_ms=200,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch("app.services.file_service.FileService.get_file", return_value=mock_record):
            response = client.get("/api/files/abc-123/")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == "abc-123"
        assert body["filename"] == "survey.kml"
        assert body["status"] == "COMPLETED"
        assert body["feature_count"] == 5


class TestGetMeasurementsEndpoint:
    def test_measurements_404_for_unknown_file(self, client):
        response = client.get("/api/files/unknown-id/measurements/")
        assert response.status_code == 404

    def test_measurements_pagination_defaults(self, client):
        from app.models.file import FileRecord, FileStatus, FileType
        from datetime import datetime, timezone

        mock_record = FileRecord(
            id="file-1",
            filename="test.kml",
            file_type=FileType.KML,
            storage_path="uploads/file-1/original/test.kml",
            status=FileStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_measurements = {
            "rows": [
                {
                    "feature_id": "feat-1",
                    "measurement_type": "AREA",
                    "value": 1245.32,
                    "unit": "m²",
                    "measurement_crs": "EPSG:32643",
                    "status": "SUCCESS",
                    "error_message": None,
                    "features": {"feature_index": 0, "geometry_type": "Polygon", "file_id": "file-1"},
                }
            ],
            "total": 1,
        }

        with patch("app.services.file_service.FileService.get_file", return_value=mock_record), \
             patch("app.services.file_service.FileService.get_measurements", return_value=mock_measurements):
            response = client.get("/api/files/file-1/measurements/")

        assert response.status_code == 200
        body = response.json()
        assert body["file_id"] == "file-1"
        assert body["page"] == 1
        assert body["page_size"] == 100
        assert body["total"] == 1
        assert len(body["measurements"]) == 1
        m = body["measurements"][0]
        assert m["geometry_type"] == "Polygon"
        assert m["measurement_type"] == "AREA"
        assert m["value"] == 1245.32
        assert m["unit"] == "m²"

    def test_measurements_page_size_exceeds_max_returns_422(self, client):
        response = client.get("/api/files/file-1/measurements/?page_size=501")
        assert response.status_code == 422

    def test_measurements_invalid_page_returns_422(self, client):
        response = client.get("/api/files/file-1/measurements/?page=0")
        assert response.status_code == 422


class TestUploadEndpointIntegration:
    """End-to-end upload tests using real KML processing but mocked persistence."""

    def test_upload_kml_with_real_processing(self, client, polygon_kml_bytes):
        """Upload a real KML file; mock only the DB/storage layer."""
        from app.models.file import FileRecord, FileStatus, FileType
        from datetime import datetime, timezone

        mock_record = FileRecord(
            id="real-proc-id",
            filename="polygon.kml",
            file_type=FileType.KML,
            storage_path="uploads/real-proc-id/original/polygon.kml",
            status=FileStatus.COMPLETED,
            original_crs="EPSG:4326",
            feature_count=1,
            processing_duration_ms=50,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with patch("app.services.file_service.FileService.process_upload", return_value=mock_record):
            response = client.post(
                "/api/files/",
                files={"file": ("polygon.kml", polygon_kml_bytes, "application/vnd.google-earth.kml+xml")},
            )

        assert response.status_code == 201
        assert response.json()["status"] == "COMPLETED"
