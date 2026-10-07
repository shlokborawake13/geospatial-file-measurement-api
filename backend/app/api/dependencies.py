from functools import lru_cache
from app.services.file_service import FileService


@lru_cache(maxsize=1)
def get_file_service() -> FileService:
    """Singleton FileService — reused across requests."""
    return FileService()
