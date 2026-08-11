import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.audit import AuditRepository
from src.schemas.audit import AuditLogCreate, AuditLogResponse


class AuditService:
    def __init__(self, db: AsyncSession):
        self.repository = AuditRepository(db)

    async def log_activity(
        self,
        organization_id: uuid.UUID,
        action: str,
        entity_type: str,
        user_id: Optional[uuid.UUID] = None,
        entity_id: Optional[uuid.UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLogResponse:
        """System activities ko async format mein record karne ka helper method."""
        log_data = AuditLogCreate(
            organization_id=organization_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
        )
        log_entry = await self.repository.create(log_data)
        return AuditLogResponse.model_validate(log_entry)

    async def get_logs_for_organization(
        self,
        organization_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        entity_type: Optional[str] = None,
    ) -> List[AuditLogResponse]:
        """Organization key audit logs retrieve karna."""
        logs = await self.repository.get_by_organization(
            organization_id=organization_id,
            limit=limit,
            offset=offset,
            entity_type=entity_type,
        )
        return [AuditLogResponse.model_validate(log) for log in logs]
