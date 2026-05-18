import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AlertCreate(BaseModel):
    query_id: uuid.UUID
    name: str
    metric_field: str
    entity_name: str
    condition_operator: str
    threshold_value: float
    check_frequency: str = "daily"
    notify_email: bool = True
    notify_slack: bool = False
    slack_webhook_url: Optional[str] = None


class AlertUpdate(BaseModel):
    name: Optional[str] = None
    threshold_value: Optional[float] = None
    check_frequency: Optional[str] = None
    notify_email: Optional[bool] = None
    notify_slack: Optional[bool] = None
    slack_webhook_url: Optional[str] = None
    is_active: Optional[bool] = None


class AlertRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    query_id: uuid.UUID
    name: str
    metric_field: str
    entity_name: str
    condition_operator: str
    threshold_value: float
    check_frequency: str
    is_active: bool
    notify_email: bool
    notify_slack: bool
    slack_webhook_url: Optional[str] = None
    last_checked_at: Optional[datetime] = None
    last_triggered_at: Optional[datetime] = None
    last_value: Optional[float] = None
    trigger_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertHistoryRead(BaseModel):
    id: uuid.UUID
    alert_id: uuid.UUID
    triggered_at: datetime
    value_at_trigger: Optional[float] = None
    channels_notified: Optional[list] = None
    notification_status: str

    model_config = {"from_attributes": True}
