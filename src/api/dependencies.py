import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import is_authenticated
from src.models.auth import User
from src.models.organization import Membership
from src.models.rbac import Permission, Role, RolePermission


class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    async def __call__(
        self,
        x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(is_authenticated),
    ):
        # 1. Fetch member with Role & Permissions in a single join query
        stmt = (
            select(Permission.name, Role.name.label("role_name"))
            .select_from(Membership)
            .join(Role, Membership.role_id == Role.id)
            .outerjoin(RolePermission, RolePermission.role_id == Role.id)
            .outerjoin(Permission, Permission.id == RolePermission.permission_id)
            .where(
                Membership.user_id == current_user.id,
                Membership.organization_id == x_organization_id,
            )
        )

        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of this organization",
            )

        # Extract role name and assigned permissions
        role_name = rows[0].role_name
        user_permissions = {row[0] for row in rows if row[0] is not None}

        # 2. Super Admin or Owner bypass check (Optional)
        if role_name in ["Super Admin", "Organization Owner"]:
            return True

        # 3. Required permission check
        if self.required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Missing required permission: '{self.required_permission}'",
            )

        return True
