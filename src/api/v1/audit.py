import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.limiter import limiter
from src.core.security import is_authenticated
from src.models.auth import User
from src.schemas.audit import AuditLogResponse
from src.services.audit import AuditService

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("/", response_model=List[AuditLogResponse])
@limiter.limit("60/minute")
@limiter.limit("60/minute")
async def get_audit_logs(
    request: Request,
    organization_id: uuid.UUID,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    entity_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
):
    audit_service = AuditService(db)
    return await audit_service.get_logs_for_organization(
        organization_id=organization_id,
        limit=limit,
        offset=offset,
        entity_type=entity_type,
    )
