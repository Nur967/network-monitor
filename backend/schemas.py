from pydantic import BaseModel, field_validator
from typing import Optional, List
from urllib.parse import urlparse
from datetime import datetime


class TargetCreate(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL must start with http:// or https://")
        if not parsed.netloc:
            raise ValueError("Invalid URL format")
        return v


class TargetResponse(BaseModel):
    id: int
    url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CheckHistoryResponse(BaseModel):
    id: int
    target_id: int
    online: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    checked_at: datetime

    model_config = {"from_attributes": True}


class MonitoringHistoryResponse(BaseModel):
    target_id: int
    checks: List[CheckHistoryResponse]


class TargetStatsResponse(BaseModel):
    target_id: int
    total_checks: int
    successful_checks: int
    uptime_percentage: float
    average_response_time_ms: Optional[float]
    last_checked_at: Optional[datetime]
    current_status: bool
