import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DataPointRead(BaseModel):
    id: uuid.UUID
    entity_name: str
    country_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    field_name: str
    field_value: Optional[float] = None
    timestamp: str
    source_type: str
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    confidence_score: float
    is_null: bool
    is_outlier: bool
    outlier_reason: Optional[str] = None
    conflicts: Optional[list] = None
    cluster_id: Optional[int] = None

    model_config = {"from_attributes": True}


class ResultRead(BaseModel):
    id: uuid.UUID
    query_id: uuid.UUID
    summary_text: Optional[str] = None
    key_findings: Optional[list] = None
    anomalies: Optional[list] = None
    data_quality_note: Optional[str] = None
    stats_summary: Optional[dict] = None
    correlation_matrix: Optional[dict] = None
    entity_rankings: Optional[list] = None
    geojson: Optional[dict] = None
    total_points: int
    null_count: int
    outlier_count: int
    created_at: datetime
    data_points: list[DataPointRead] = []

    model_config = {"from_attributes": True}


class CountryResultRead(BaseModel):
    country_code: str
    entity_name: str
    data_points: list[DataPointRead]
    sparklines: Optional[dict] = None
