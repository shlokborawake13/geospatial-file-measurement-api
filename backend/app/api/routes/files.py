"""
Files API Routes
================

POST   /api/files/                      Upload a KML or Shapefile ZIP
GET    /api/files/{file_id}/            Get file metadata
GET    /api/files/{file_id}/measurements/  Get paginated measurements
"""
import logging
from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.dependencies import get_file_service
from app.schemas.file import FileDetailResponse, FileUploadResponse
from app.schemas.measurement import MeasurementResponse, MeasurementsResponse
from app.services.file_service import FileService

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_PAGE_SIZE = 500


@router.post(
    "/",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a KML or Shapefile ZIP",
)
async def upload_file(
    file: UploadFile = File(..., description="KML file or Shapefile ZIP archive"),
    service: FileService = Depends(get_file_service),
) -> FileUploadResponse:
    record = await service.process_upload(file)
    return FileUploadResponse(
        id=record.id,
        filename=record.filename,
        file_type=record.file_type,
        feature_count=record.feature_count,
        crs=record.original_crs,
        status=record.status,
    )


@router.get(
    "/{file_id}/",
    response_model=FileDetailResponse,
    summary="Get file metadata",
)
def get_file(
    file_id: str,
    service: FileService = Depends(get_file_service),
) -> FileDetailResponse:
    record = service.get_file(file_id)
    return FileDetailResponse(
        id=record.id,
        filename=record.filename,
        file_type=record.file_type,
        feature_count=record.feature_count,
        crs=record.original_crs,
        status=record.status,
        error_message=record.error_message,
        processing_duration_ms=record.processing_duration_ms,
        created_at=record.created_at,
    )


@router.get(
    "/{file_id}/measurements/",
    response_model=MeasurementsResponse,
    summary="Get paginated measurements for a file",
)
def get_measurements(
    file_id: str,
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(default=100, ge=1, le=MAX_PAGE_SIZE, description="Results per page"),
    service: FileService = Depends(get_file_service),
) -> MeasurementsResponse:
    result = service.get_measurements(file_id, page, page_size)
    rows = result["rows"]
    total = result["total"]

    measurements = [
        MeasurementResponse(
            feature_id=row["feature_id"],
            feature_index=row["features"]["feature_index"],
            geometry_type=row["features"]["geometry_type"],
            measurement_type=row.get("measurement_type"),
            value=row.get("value"),
            unit=row.get("unit"),
            measurement_crs=row.get("measurement_crs"),
            status=row["status"],
        )
        for row in rows
    ]

    return MeasurementsResponse(
        file_id=file_id,
        page=page,
        page_size=page_size,
        total=total,
        measurements=measurements,
    )
