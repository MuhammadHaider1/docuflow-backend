import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.organization import (
    Membership,  # Apne model ka exact import adjust kar lein
)
from src.models.rbac import Permission, Role


class RBACService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------------------------------------------------------
    # 1. Global Lookups
    # ---------------------------------------------------------
    async def get_all_roles(self):
        """Fetches all system roles."""
        result = await self.db.execute(select(Role))
        return result.scalars().all()

    async def get_all_permissions(self):
        """Fetches all system permissions."""
        result = await self.db.execute(select(Permission))
        return result.scalars().all()

    # ---------------------------------------------------------
    # 2. Member Role Assignment / Change
    # ---------------------------------------------------------
    async def assign_role_to_member(
        self, org_id: uuid.UUID, user_id: uuid.UUID, role_id: uuid.UUID
    ):
        """Assigns or updates a role for an organization member."""
        # Check if the requested role actually exists
        role_result = await self.db.execute(select(Role).where(Role.id == role_id))
        role = role_result.scalars().first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
            )

        # Fetch membership entry
        query = select(Membership).where(
            Membership.organization_id == org_id, Membership.user_id == user_id
        )
        result = await self.db.execute(query)
        membership = result.scalars().first()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this organization",
            )

        # Update role and commit
        membership.role_id = role_id
        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    # ---------------------------------------------------------
    # 3. Revoke Role
    # ---------------------------------------------------------
    async def revoke_role_from_member(self, org_id: uuid.UUID, user_id: uuid.UUID):
        query = select(Membership).where(
            Membership.organization_id == org_id, Membership.user_id == user_id
        )
        result = await self.db.execute(query)
        membership = result.scalars().first()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this organization",
            )

        # Fetch Default 'Viewer' Role
        viewer_role_query = select(Role).where(Role.name == "Viewer")
        role_result = await self.db.execute(viewer_role_query)
        viewer_role = role_result.scalars().first()

        if not viewer_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Default Viewer role not found",
            )

        # Assign Viewer Role instead of None
        membership.role_id = viewer_role.id
        await self.db.commit()
        await self.db.refresh(membership)

        return {
            "message": "Role reset to default Viewer role",
            "user_id": str(user_id),
            "organization_id": str(org_id),
        }

    # ---------------------------------------------------------
    # 4. Get Member Role
    # ---------------------------------------------------------
    async def get_member_role(self, org_id: uuid.UUID, user_id: uuid.UUID):
        """Retrieves current role assigned to a member in an organization."""
        query = select(Membership).where(
            Membership.organization_id == org_id, Membership.user_id == user_id
        )
        result = await self.db.execute(query)
        membership = result.scalars().first()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this organization",
            )

        if not membership.role_id:
            return {"user_id": user_id, "organization_id": org_id, "role": None}

        role_result = await self.db.execute(
            select(Role).where(Role.id == membership.role_id)
        )
        role = role_result.scalars().first()

        return {"user_id": user_id, "organization_id": org_id, "role": role}
