from pydantic import BaseModel
from typing import Any, Dict, Optional


class FeatureResponse(BaseModel):
    id: str
    file_id: str
    feature_index: int
    geometry_type: str
    geometry: Optional[Dict[str, Any]]
    properties: Optional[Dict[str, Any]]
    original_crs: Optional[str]

    model_config = {"from_attributes": True}
