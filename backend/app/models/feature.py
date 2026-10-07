from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class Feature:
    id: str
    file_id: str
    feature_index: int
    geometry_type: str
    geometry: Optional[Dict[str, Any]]   # GeoJSON dict stored as JSONB
    properties: Optional[Dict[str, Any]]  # Source attributes stored as JSONB
    original_crs: Optional[str]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
