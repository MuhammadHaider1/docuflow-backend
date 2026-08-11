import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit import AuditLog
from src.schemas.audit import AuditLogCreate


class AuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, log_in: AuditLogCreate) -> AuditLog:
        db_log = AuditLog(**log_in.model_dump())
        self.db.add(db_log)
        await self.db.commit()
        await self.db.refresh(db_log)
        return db_log

    async def get_by_organization(
        self,
        organization_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        entity_type: Optional[str] = None,
    ) -> List[AuditLog]:
        query = select(AuditLog).where(AuditLog.organization_id == organization_id)

        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)

        query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
