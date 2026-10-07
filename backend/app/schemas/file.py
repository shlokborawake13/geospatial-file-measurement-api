from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.file import FileType, FileStatus


class FileUploadResponse(BaseModel):
    id: str
    filename: str
    file_type: FileType
    feature_count: Optional[int]
    crs: Optional[str]
    status: FileStatus

    model_config = {"from_attributes": True}


class FileDetailResponse(BaseModel):
    id: str
    filename: str
    file_type: FileType
    feature_count: Optional[int]
    crs: Optional[str]
    status: FileStatus
    error_message: Optional[str]
    processing_duration_ms: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}
