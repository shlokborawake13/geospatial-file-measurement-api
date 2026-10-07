"""
File Service
============

Orchestrates the complete upload and processing pipeline:

    validate
    → create file record (UPLOADED)
    → upload original file to Supabase Storage
    → update status (PROCESSING)
    → parse into GeoDataFrame
    → process features + measurements
    → persist features
    → persist measurements
    → update file record (COMPLETED)

On any unrecoverable error:
    → update file record (FAILED)
    → re-raise so the API layer can return an appropriate response
"""
import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ProcessingFailedError
from app.models.file import FileRecord, FileStatus, FileType
from app.repositories.feature_repository import FeatureRepository
from app.repositories.file_repository import FileRepository
from app.repositories.measurement_repository import MeasurementRepository
from app.services.file_validator import FileValidator
from app.services.geospatial_processor import GeospatialProcessor
from app.services.kml_processor import KMLProcessor
from app.services.shapefile_processor import ShapefileProcessor
from app.utils.storage import StorageService, get_storage_content_type

logger = logging.getLogger(__name__)


class FileService:
    def __init__(self):
        self._validator = FileValidator()
        self._kml_processor = KMLProcessor()
        self._shp_processor = ShapefileProcessor()
        self._geo_processor = GeospatialProcessor()
        self._file_repo = FileRepository()
        self._feature_repo = FeatureRepository()
        self._measurement_repo = MeasurementRepository()
        self._storage = StorageService()

    async def process_upload(self, upload: UploadFile) -> FileRecord:
        """
        Full upload + processing pipeline.

        Returns the completed FileRecord.
        Raises AppError subclasses on validation failures.
        Raises ProcessingFailedError on unrecoverable processing errors.
        """
        content = await upload.read()
        filename = upload.filename or "upload"

        # 1. Validate
        ext = self._validator.validate(filename, content)
        file_type = FileType.KML if ext == "kml" else FileType.SHP_ZIP
        content_type = get_storage_content_type(file_type)
        file_id = str(uuid.uuid4())

        logger.info(
            "Upload started: file_id=%s filename=%s size=%d content_type=%s",
            file_id, filename, len(content), content_type,
        )

        # 2. Create initial record
        storage_path = f"uploads/{file_id}/original/{filename}"
        now = datetime.now(timezone.utc)
        record = FileRecord(
            id=file_id,
            filename=filename,
            file_type=file_type,
            storage_path=storage_path,
            status=FileStatus.UPLOADED,
            created_at=now,
            updated_at=now,
        )
        self._file_repo.insert(record)

        # 3. Upload original file to Supabase Storage
        upload_start_ms = time.monotonic()
        try:
            self._storage.upload(
                path=storage_path,
                content=content,
                content_type=content_type,
            )
            logger.info("File stored: %s", storage_path)
        except Exception as exc:
            duration_ms = int((time.monotonic() - upload_start_ms) * 1000)
            logger.exception("Storage upload failed: file_id=%s error=%s", file_id, exc)
            self._file_repo.update_status(
                file_id,
                FileStatus.FAILED,
                error_message="Storage upload failed.",
                processing_duration_ms=duration_ms,
            )
            from app.core.exceptions import AppError, StorageUploadError
            if isinstance(exc, AppError):
                raise
            raise StorageUploadError("The uploaded file could not be stored.") from exc

        # 4. Process
        start_ms = time.monotonic()
        try:
            self._file_repo.update_status(file_id, FileStatus.PROCESSING)

            # Parse into GeoDataFrame
            if file_type == FileType.KML:
                gdf = self._kml_processor.process(content)
            else:
                gdf = self._shp_processor.process(content)

            # Run common pipeline
            features, measurements, original_crs, _ = self._geo_processor.process(gdf, file_id)

            # Persist
            self._feature_repo.bulk_insert(features)
            self._measurement_repo.bulk_insert(measurements)

            duration_ms = int((time.monotonic() - start_ms) * 1000)
            self._file_repo.update_status(
                file_id,
                FileStatus.COMPLETED,
                feature_count=len(features),
                original_crs=original_crs,
                processing_duration_ms=duration_ms,
            )
            record.status = FileStatus.COMPLETED
            record.feature_count = len(features)
            record.original_crs = original_crs
            record.processing_duration_ms = duration_ms

            logger.info(
                "Processing completed: file_id=%s features=%d duration_ms=%d",
                file_id, len(features), duration_ms,
            )
            return record

        except Exception as exc:
            duration_ms = int((time.monotonic() - start_ms) * 1000)
            error_msg = str(exc)
            logger.exception("Processing failed: file_id=%s error=%s", file_id, error_msg)
            self._file_repo.update_status(
                file_id,
                FileStatus.FAILED,
                error_message=error_msg,
                processing_duration_ms=duration_ms,
            )
            # Re-raise AppErrors as-is; wrap unexpected errors
            from app.core.exceptions import AppError
            if isinstance(exc, AppError):
                raise
            raise ProcessingFailedError(f"Processing failed: {error_msg}") from exc

    def get_file(self, file_id: str) -> FileRecord:
        from app.core.exceptions import FileNotFoundError
        record = self._file_repo.get(file_id)
        if record is None:
            raise FileNotFoundError(f"File '{file_id}' not found.")
        return record

    def get_measurements(self, file_id: str, page: int, page_size: int) -> dict:
        from app.core.exceptions import FileNotFoundError, FileNotReadyError
        record = self._file_repo.get(file_id)
        if record is None:
            raise FileNotFoundError(f"File '{file_id}' not found.")
        if record.status not in (FileStatus.COMPLETED, FileStatus.FAILED):
            raise FileNotReadyError(
                f"File is currently '{record.status.value}'. Measurements are available after processing completes."
            )

        rows, total = self._measurement_repo.get_paginated_by_file(file_id, page, page_size)
        return {"rows": rows, "total": total}
