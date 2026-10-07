"""
Storage Service
===============

Wraps Supabase Storage operations.
All storage interactions go through this class.
"""
import logging
from typing import Union
from storage3.utils import StorageException
from app.core.config import settings
from app.core.exceptions import StorageUploadError, UnsupportedFileTypeError
from app.models.file import FileType
from app.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# Authoritative server-side MIME type map — never trust the browser value.
_MIME_TYPES: dict[str, str] = {
    FileType.KML.value: "application/vnd.google-earth.kml+xml",
    FileType.SHP_ZIP.value: "application/zip",
}


def get_storage_content_type(file_type: Union[FileType, str]) -> str:
    """
    Return the authoritative server-side MIME type for a FileType enum or string.
    Never uses or trusts client-supplied MIME types.
    """
    val = file_type.value if isinstance(file_type, FileType) else str(file_type)
    val_upper = val.upper()
    if val_upper in _MIME_TYPES:
        return _MIME_TYPES[val_upper]
    if val_upper == "ZIP":
        return _MIME_TYPES[FileType.SHP_ZIP.value]
    raise UnsupportedFileTypeError(f"Unsupported file type for storage: {file_type}")


class StorageService:
    def __init__(self):
        self._client = get_supabase_client()
        self._bucket = settings.SUPABASE_STORAGE_BUCKET

    def upload(self, path: str, content: bytes, content_type: str) -> None:
        """
        Upload raw bytes to Supabase Storage.

        content_type must be the server-determined MIME type, never the
        browser-supplied value.  The storage3 SDK passes this as the
        multipart Content-Type, which Supabase validates against the
        bucket's allowed_mime_types list.
        """
        try:
            self._client.storage.from_(self._bucket).upload(
                path=path,
                file=content,
                file_options={"content-type": content_type, "upsert": "true"},
            )
        except StorageException as exc:
            logger.error("[STORAGE] Upload failed path=%s error=%s", path, exc)
            raise StorageUploadError("The uploaded file could not be stored.") from exc
        except Exception as exc:
            logger.error("[STORAGE] Unexpected upload failure path=%s error=%s", path, exc)
            raise StorageUploadError("The uploaded file could not be stored.") from exc
        logger.info("[STORAGE] Uploaded path=%s content_type=%s", path, content_type)

    def get_public_url(self, path: str) -> str:
        """Return the public URL for a stored file."""
        return self._client.storage.from_(self._bucket).get_public_url(path)
