"""
File Validator
==============

Validates uploaded files before any processing begins.

Checks:
- File extension (whitelist)
- File size (configurable MAX_UPLOAD_SIZE_MB)
- Basic content integrity (ZIP magic bytes, KML XML structure)
"""
import zipfile
import logging
from app.core.config import settings
from app.core.exceptions import (
    UnsupportedFileTypeError,
    FileTooLargeError,
    InvalidFileError,
    InvalidKMLError,
    InvalidShapefileError,
)

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"kml", "zip"}
KML_MAGIC = b"<?xml"
ZIP_MAGIC = b"PK\x03\x04"


class FileValidator:
    def validate(self, filename: str, content: bytes) -> str:
        """
        Validate the uploaded file.

        Returns the normalised extension ('kml' or 'zip').
        Raises an AppError subclass on any validation failure.
        """
        ext = self._check_extension(filename)
        self._check_size(content, filename)
        self._check_content(ext, content, filename)
        return ext

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _check_extension(filename: str) -> str:
        if "." not in filename:
            raise UnsupportedFileTypeError(
                f"'{filename}' has no file extension. Accepted: .kml, .zip"
            )
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(
                f"'.{ext}' is not supported. Accepted: .kml, .zip"
            )
        return ext

    @staticmethod
    def _check_size(content: bytes, filename: str) -> None:
        max_bytes = settings.max_upload_size_bytes
        if len(content) > max_bytes:
            raise FileTooLargeError(
                f"'{filename}' is {len(content) // (1024*1024)} MB. "
                f"Maximum allowed size is {settings.MAX_UPLOAD_SIZE_MB} MB."
            )

    @staticmethod
    def _check_content(ext: str, content: bytes, filename: str) -> None:
        if ext == "zip":
            if not content.startswith(ZIP_MAGIC):
                raise InvalidShapefileError(
                    f"'{filename}' does not appear to be a valid ZIP archive."
                )
            if not zipfile.is_zipfile(__import__("io").BytesIO(content)):
                raise InvalidShapefileError(
                    f"'{filename}' is not a readable ZIP archive."
                )
        elif ext == "kml":
            # KML must be valid XML starting with an XML declaration or <kml
            stripped = content.lstrip()
            if not (stripped.startswith(b"<?xml") or stripped.startswith(b"<kml")):
                raise InvalidKMLError(
                    f"'{filename}' does not appear to be a valid KML file."
                )
