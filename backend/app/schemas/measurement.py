from pydantic import BaseModel
from typing import List, Optional
from app.models.measurement import MeasurementType, MeasurementStatus


class MeasurementResponse(BaseModel):
    feature_id: str
    feature_index: int
    geometry_type: str
    measurement_type: Optional[MeasurementType]
    value: Optional[float]
    unit: Optional[str]
    measurement_crs: Optional[str]
    status: MeasurementStatus

    model_config = {"from_attributes": True}


class MeasurementsResponse(BaseModel):
    file_id: str
    page: int
    page_size: int
    total: int
    measurements: List[MeasurementResponse]
