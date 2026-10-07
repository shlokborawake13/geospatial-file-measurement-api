from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ── Custom exception hierarchy ────────────────────────────────────────────────

class AppError(Exception):
    """Base application error."""
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class UnsupportedFileTypeError(AppError):
    def __init__(self, message: str = "Unsupported file type."):
        super().__init__("UNSUPPORTED_FILE_TYPE", message, 400)


class FileTooLargeError(AppError):
    def __init__(self, message: str = "File exceeds the maximum allowed size."):
        super().__init__("FILE_TOO_LARGE", message, 413)


class InvalidFileError(AppError):
    def __init__(self, message: str = "The uploaded file is invalid."):
        super().__init__("INVALID_FILE", message, 400)


class InvalidKMLError(AppError):
    def __init__(self, message: str = "The uploaded KML file could not be parsed."):
        super().__init__("INVALID_KML", message, 400)


class InvalidShapefileError(AppError):
    def __init__(self, message: str = "The uploaded Shapefile is invalid."):
        super().__init__("INVALID_SHAPEFILE", message, 400)


class MissingShapefileComponentError(AppError):
    def __init__(self, message: str = "Required Shapefile components are missing."):
        super().__init__("MISSING_SHAPEFILE_COMPONENT", message, 400)


class InvalidCRSError(AppError):
    def __init__(self, message: str = "CRS information is missing or invalid."):
        super().__init__("INVALID_CRS", message, 400)


class UnsupportedGeometryError(AppError):
    def __init__(self, message: str = "Geometry type is not supported."):
        super().__init__("UNSUPPORTED_GEOMETRY", message, 400)


class FileNotFoundError(AppError):
    def __init__(self, message: str = "File not found."):
        super().__init__("FILE_NOT_FOUND", message, 404)


class FileNotReadyError(AppError):
    def __init__(self, message: str = "File processing is not complete."):
        super().__init__("FILE_NOT_READY", message, 409)


class ProcessingFailedError(AppError):
    def __init__(self, message: str = "File processing failed."):
        super().__init__("PROCESSING_FAILED", message, 500)


class MeasurementFailedError(AppError):
    def __init__(self, message: str = "Measurement calculation failed."):
        super().__init__("MEASUREMENT_FAILED", message, 500)


class DatabaseError(AppError):
    def __init__(self, message: str = "A database error occurred."):
        super().__init__("DATABASE_ERROR", message, 500)


class StorageUploadError(AppError):
    def __init__(self, message: str = "The uploaded file could not be stored."):
        super().__init__("STORAGE_UPLOAD_FAILED", message, 500)


# ── FastAPI exception handler registration ────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        import logging
        logging.getLogger(__name__).exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}},
        )
