from pydantic import BaseModel
from typing import List, Optional

class TemporalDataPoint(BaseModel):
    version: str
    published_at: str
    fan_out: int
    global_fan_in: Optional[int] = None
    vuln_count: int = 0

class TemporalReport(BaseModel):
    ecosystem: str
    package_name: str
    data_points: List[TemporalDataPoint]
    total_versions_available: int
    sampled_versions: int
