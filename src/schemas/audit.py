import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class AuditLogBase(BaseModel):
    action: str
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None


class AuditLogCreate(AuditLogBase):
    organization_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None


class AuditLogResponse(AuditLogBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
