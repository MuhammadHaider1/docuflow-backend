import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.organization import Membership, Organization
from src.schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, obj_in: OrganizationCreate) -> Organization:
        db_obj = Organization(**obj_in.model_dump())
        self.db.add(db_obj)
        await self.db.flush()  # ID generate karne ke liye
        return db_obj

    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    # User ki sari organizations (via Membership table join)
    async def get_user_organizations(self, user_id: uuid.UUID) -> List[Organization]:
        stmt = (
            select(Organization)
            .join(Membership, Organization.id == Membership.organization_id)
            .where(Membership.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self, db_obj: Organization, obj_in: OrganizationUpdate
    ) -> Organization:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        await self.db.flush()
        return db_obj

    async def delete(self, db_obj: Organization) -> None:
        await self.db.delete(db_obj)
        await self.db.flush()

    async def create_membership(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        role_id: Optional[uuid.UUID] = None,
    ) -> Membership:
        db_obj = Membership(
            user_id=user_id,
            organization_id=org_id,
            role_id=role_id,
        )
        self.db.add(db_obj)
        await self.db.flush()
        return db_obj

    async def get_membership(
        self, user_id: uuid.UUID, org_id: uuid.UUID
    ) -> Membership | None:
        stmt = select(Membership).where(
            Membership.user_id == user_id, Membership.organization_id == org_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
