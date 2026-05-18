import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    service_name: str
    api_key: str


class ApiKeyRead(BaseModel):
    id: uuid.UUID
    service_name: str
    key_preview: Optional[str] = None
    is_valid: bool
    last_tested_at: Optional[datetime] = None
    rate_limit_info: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyTestResult(BaseModel):
    success: bool
    message: str
    rate_limit_info: Optional[dict] = None
