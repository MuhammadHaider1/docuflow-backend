from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationBase(BaseModel):
    title: str
    message: str
    notification_type: str = "INFO"
    payload: Optional[Dict[str, Any]] = None


class NotificationCreate(BaseModel):
    user_id: UUID
    title: str
    message: str
    notification_type: str = "INFO"
    payload: Optional[Dict[str, Any]] = None


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    message: str
    notification_type: str
    payload: Optional[Dict[str, Any]] = None
    is_read: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationUpdate(BaseModel):
    is_read: bool
