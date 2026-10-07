"""Tests focused on the upload pipeline."""
import pytest
from unittest.mock import patch
from app.models.file import FileRecord, FileStatus, FileType
from datetime import datetime, timezone


def _mock_record(file_type=FileType.KML, status=FileStatus.COMPLETED, feature_count=3):
    return FileRecord(
        id="upload-test-id",
        filename="test.kml",
        file_type=file_type,
        storage_path="uploads/upload-test-id/original/test.kml",
        status=status,
        original_crs="EPSG:4326",
        feature_count=feature_count,
        processing_duration_ms=100,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_upload_kml_returns_201(client, polygon_kml_bytes):
    with patch("app.services.file_service.FileService.process_upload", return_value=_mock_record()):
        response = client.post(
            "/api/files/",
            files={"file": ("polygon.kml", polygon_kml_bytes, "application/vnd.google-earth.kml+xml")},
        )
    assert response.status_code == 201
    assert response.json()["file_type"] == "KML"


def test_upload_zip_returns_201(client, valid_zip_bytes):
    with patch(
        "app.services.file_service.FileService.process_upload",
        return_value=_mock_record(file_type=FileType.SHP_ZIP),
    ):
        response = client.post(
            "/api/files/",
            files={"file": ("valid.zip", valid_zip_bytes, "application/zip")},
        )
    assert response.status_code == 201
    assert response.json()["file_type"] == "SHP_ZIP"


def test_upload_no_file_returns_422(client):
    response = client.post("/api/files/")
    assert response.status_code == 422


def test_upload_wrong_extension_returns_400(client):
    response = client.post(
        "/api/files/",
        files={"file": ("data.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_upload_response_has_required_fields(client, polygon_kml_bytes):
    with patch("app.services.file_service.FileService.process_upload", return_value=_mock_record()):
        response = client.post(
            "/api/files/",
            files={"file": ("polygon.kml", polygon_kml_bytes, "application/vnd.google-earth.kml+xml")},
        )
    body = response.json()
    for field in ("id", "filename", "file_type", "status", "feature_count", "crs"):
        assert field in body, f"Missing field: {field}"


def test_get_storage_content_type():
    from app.utils.storage import get_storage_content_type
    from app.core.exceptions import UnsupportedFileTypeError

    assert get_storage_content_type(FileType.KML) == "application/vnd.google-earth.kml+xml"
    assert get_storage_content_type(FileType.SHP_ZIP) == "application/zip"
    assert get_storage_content_type("KML") == "application/vnd.google-earth.kml+xml"
    assert get_storage_content_type("SHP_ZIP") == "application/zip"
    assert get_storage_content_type("kml") == "application/vnd.google-earth.kml+xml"
    assert get_storage_content_type("zip") == "application/zip"

    with pytest.raises(UnsupportedFileTypeError):
        get_storage_content_type("UNKNOWN")


def test_storage_service_upload_passes_correct_file_options(mock_supabase):
    from app.utils.storage import StorageService

    service = StorageService()
    test_path = "uploads/123/original/lines.kml"
    test_content = b"<kml>content</kml>"
    test_mime = "application/vnd.google-earth.kml+xml"

    service.upload(test_path, test_content, test_mime)

    mock_supabase.storage.from_.return_value.upload.assert_called_once_with(
        path=test_path,
        file=test_content,
        file_options={"content-type": test_mime, "upsert": "true"},
    )


def test_storage_service_upload_handles_storage_exception(mock_supabase):
    from storage3.utils import StorageException
    from app.core.exceptions import StorageUploadError
    from app.utils.storage import StorageService

    mock_supabase.storage.from_.return_value.upload.side_effect = StorageException(
        {"statusCode": 400, "error": "invalid_mime_type", "message": "mime type text/plain is not supported"}
    )
    service = StorageService()

    with pytest.raises(StorageUploadError) as exc_info:
        service.upload("test/path", b"content", "application/vnd.google-earth.kml+xml")

    assert exc_info.value.code == "STORAGE_UPLOAD_FAILED"
    assert exc_info.value.message == "The uploaded file could not be stored."


@pytest.mark.asyncio
async def test_process_upload_determines_mime_server_side_ignoring_browser_mime(lines_kml_bytes):
    from io import BytesIO
    from fastapi import UploadFile
    from app.services.file_service import FileService

    service = FileService()
    upload = UploadFile(
        file=BytesIO(lines_kml_bytes),
        filename="lines.kml",
        headers={"content-type": "text/plain"},
    )

    with patch.object(service._storage, "upload") as mock_upload:
        record = await service.process_upload(upload)

    assert record.file_type == FileType.KML
    mock_upload.assert_called_once()
    _, kwargs = mock_upload.call_args
    assert kwargs["content_type"] == "application/vnd.google-earth.kml+xml"


@pytest.mark.asyncio
async def test_process_upload_storage_failure_updates_db_to_failed(lines_kml_bytes):
    from io import BytesIO
    from fastapi import UploadFile
    from app.core.exceptions import StorageUploadError
    from app.services.file_service import FileService

    service = FileService()
    upload = UploadFile(
        file=BytesIO(lines_kml_bytes),
        filename="lines.kml",
        headers={"content-type": "text/plain"},
    )

    with patch.object(service._storage, "upload", side_effect=StorageUploadError("The uploaded file could not be stored.")), \
         patch.object(service._file_repo, "update_status") as mock_update_status:
        with pytest.raises(StorageUploadError):
            await service.process_upload(upload)

    # Verify database record was marked as FAILED
    mock_update_status.assert_called_once()
    call_args = mock_update_status.call_args
    assert call_args[0][1] == FileStatus.FAILED
    assert call_args[1]["error_message"] == "Storage upload failed."


def test_api_upload_storage_failure_returns_500_json_error(client, lines_kml_bytes):
    from app.core.exceptions import StorageUploadError

    with patch("app.utils.storage.StorageService.upload", side_effect=StorageUploadError("The uploaded file could not be stored.")):
        response = client.post(
            "/api/files/",
            files={"file": ("lines.kml", lines_kml_bytes, "text/plain")},
        )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "STORAGE_UPLOAD_FAILED",
            "message": "The uploaded file could not be stored.",
        }
    }
