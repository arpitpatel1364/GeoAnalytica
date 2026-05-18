import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class ExportCreate(BaseModel):
    query_id: uuid.UUID
    format: str
    is_scheduled: bool = False
    schedule_frequency: Optional[str] = None
    schedule_email: Optional[EmailStr] = None


class ExportRead(BaseModel):
    id: uuid.UUID
    query_id: uuid.UUID
    format: str
    is_scheduled: bool
    schedule_frequency: Optional[str] = None
    schedule_email: Optional[str] = None
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    is_public: bool
    public_token: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
