# datasource.py
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DatasourceRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    source_type: str
    file_size_bytes: Optional[int] = None
    row_count: Optional[int] = None
    columns: Optional[list] = None
    preview: Optional[list] = None
    created_at: datetime

    model_config = {"from_attributes": True}
