import uuid
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.organization import Organization
from src.repositories.organization import OrganizationRepository
from src.repositories.user import UserRepository
from src.schemas.organization import OrganizationCreate, OrganizationUpdate

# Role granted to whoever creates an organization.
OWNER_ROLE_NAME = "Organization Owner"


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.user_repo = UserRepository(db)

    async def register_new_organization(
        self, payload: OrganizationCreate, user_id: uuid.UUID
    ) -> Organization:
        # 1. Check duplicate slug
        existing_org = await self.org_repo.get_by_slug(payload.slug)
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slug is already in use, please try a different one.",
            )

        # 2. The creator owns the new organization, so they get the owner role.
        owner_role = await self.user_repo.get_role_by_name(OWNER_ROLE_NAME)
        if not owner_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Default role '{OWNER_ROLE_NAME}' does not exist in database. "
                    "Please run the RBAC seeder."
                ),
            )

        try:
            # 3. Create Organization
            new_org = await self.org_repo.create(payload)

            # 4. Attach Creator as owner
            await self.org_repo.create_membership(
                user_id=user_id, org_id=new_org.id, role_id=owner_role.id
            )

            # Commit both operations together
            await self.db.commit()
            await self.db.refresh(new_org)

            return new_org

        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to onboard organization: {str(e)}",
            )

    async def get_user_organizations(self, user_id: uuid.UUID) -> List[Organization]:
        """User ki saari joined organizations fetch karta hai."""
        return await self.org_repo.get_user_organizations(user_id=user_id)

    async def get_organization_details(
        self, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> Organization:
        """Organization detail fetch karta hai after checking user membership authorization."""
        membership = await self.org_repo.get_membership(user_id=user_id, org_id=org_id)
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a member of this organization.",
            )

        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )

        return org

    async def update_organization_details(
        self, org_id: uuid.UUID, payload: OrganizationUpdate, user_id: uuid.UUID
    ) -> Organization:
        """Organization name/slug update karta hai with slug uniqueness check."""
        # 1. Access & Membership check
        org = await self.get_organization_details(org_id=org_id, user_id=user_id)

        # 2. If updating slug, check if the new slug is already taken
        if payload.slug and payload.slug != org.slug:
            existing_slug = await self.org_repo.get_by_slug(payload.slug)
            if existing_slug:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Slug is already in use, please try a different one.",
                )

        try:
            updated_org = await self.org_repo.update(db_obj=org, obj_in=payload)
            await self.db.commit()
            await self.db.refresh(updated_org)
            return updated_org
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update organization: {str(e)}",
            )

    async def delete_organization(self, org_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Organization ko permanently remove karta hai."""
        org = await self.get_organization_details(org_id=org_id, user_id=user_id)

        try:
            await self.org_repo.delete(db_obj=org)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete organization: {str(e)}",
            )
