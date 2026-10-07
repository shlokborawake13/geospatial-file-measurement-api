from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum


class MeasurementType(str, Enum):
    AREA = "AREA"
    LENGTH = "LENGTH"


class MeasurementStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NOT_REQUIRED = "NOT_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"


@dataclass
class Measurement:
    id: str
    feature_id: str
    status: MeasurementStatus
    measurement_type: Optional[MeasurementType] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    measurement_crs: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
