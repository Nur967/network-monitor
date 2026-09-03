from pydantic import BaseModel, field_validator
from typing import Optional
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
