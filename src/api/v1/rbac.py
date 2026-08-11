import uuid

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import PermissionChecker
from src.core.database import get_db
from src.core.security import is_authenticated
from src.models.auth import User
from src.schemas.rbac import AssignRoleRequest, RevokeRoleRequest
from src.services.rbac import RBACService

router = APIRouter(prefix="/rbac", tags=["RBAC"])


# ==========================================
# Lookups (System-wide Global)
# ==========================================


@router.get("/roles")
async def get_all_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
):
    service = RBACService(db)
    return await service.get_all_roles()


@router.get("/permissions")
async def get_all_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
):
    service = RBACService(db)
    return await service.get_all_permissions()


# ==========================================
# Role Management Endpoints
# ==========================================


@router.post("/assign-role", status_code=status.HTTP_200_OK)
async def assign_role_to_member(
    payload: AssignRoleRequest,
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("members:manage_roles")),
):
    service = RBACService(db)
    # 👈 Security Fix: Header ki organization_id pass ho rahi hai
    return await service.assign_role_to_member(
        org_id=x_organization_id, user_id=payload.user_id, role_id=payload.role_id
    )


@router.post("/revoke-role", status_code=status.HTTP_200_OK)
async def revoke_role_from_member(
    payload: RevokeRoleRequest,
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("members:manage_roles")),
):
    service = RBACService(db)
    # 👈 Security Fix: Header ki organization_id pass ho rahi hai
    return await service.revoke_role_from_member(
        org_id=x_organization_id, user_id=payload.user_id
    )


@router.get("/members/{user_id}/role")
async def get_member_role(
    user_id: uuid.UUID,
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("organization:read")),
):
    service = RBACService(db)
    return await service.get_member_role(org_id=x_organization_id, user_id=user_id)
