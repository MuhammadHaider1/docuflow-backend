import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.organization import Membership
from src.models.rbac import Permission, Role, RolePermission


class RBACRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_roles(self) -> Sequence[Role]:
        stmt = select(Role)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_all_permissions(self) -> Sequence[Permission]:
        stmt = select(Permission)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_role_by_id(self, role_id: uuid.UUID) -> Role | None:
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_role_by_name(self, name: str) -> Role | None:
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.name == name)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_permission_by_name(self, name: str) -> Permission | None:
        stmt = select(Permission).where(Permission.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_role(self, name: str, description: str | None = None) -> Role:
        role = Role(name=name, description=description)
        self.db.add(role)
        await self.db.flush()
        return role

    async def create_permission(
        self, name: str, description: str | None = None
    ) -> Permission:
        permission = Permission(name=name, description=description)
        self.db.add(permission)
        await self.db.flush()
        return permission

    async def assign_permission_to_role(
        self, role: Role, permission: Permission
    ) -> None:
        if permission not in role.permissions:
            role.permissions.append(permission)

    async def check_user_permission(
        self, user_id: uuid.UUID, org_id: uuid.UUID, permission_name: str
    ) -> bool:
        stmt = (
            select(Permission.id)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(Membership, Membership.role_id == Role.id)
            .where(
                Membership.user_id == user_id,
                Membership.organization_id == org_id,
                Permission.name == permission_name,
            )
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
