from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum


class FileType(str, Enum):
    KML = "KML"
    SHP_ZIP = "SHP_ZIP"


class FileStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class FileRecord:
    id: str
    filename: str
    file_type: FileType
    storage_path: str
    status: FileStatus
    original_crs: Optional[str] = None
    feature_count: Optional[int] = None
    error_message: Optional[str] = None
    processing_duration_ms: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
