from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.schemas.common import AlertType, PaginatedResponse


class AlertResponse(BaseModel):
    id: int
    alert_type: AlertType
    severity: str
    message: str
    title_name: Optional[str] = None
    data: Optional[dict] = None
    is_read: bool
    created_at: datetime


class AlertListResponse(PaginatedResponse):
    alerts: list[AlertResponse]
    unread_count: int = 0
