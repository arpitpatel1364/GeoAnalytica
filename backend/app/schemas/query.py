import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class QueryCreate(BaseModel):
    project_id: uuid.UUID
    instruction_text: str
    mode: str = "natural"


class QueryRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    instruction_text: str
    mode: str
    status: str
    parsed_spec: Optional[dict] = None
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    data_point_count: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class QueryHistoryItem(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    instruction_text: str
    status: str
    duration_seconds: Optional[float] = None
    data_point_count: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}
