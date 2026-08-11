import uuid
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import is_authenticated
from src.models.auth import User
from src.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from src.services.organization import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations"])


# 1. Create Organization
@router.post(
    "/",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_organization(
    payload: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
):
    org_service = OrganizationService(db)
    return await org_service.register_new_organization(
        payload=payload, user_id=current_user.id
    )


# 2. Get All Organizations of Current User
@router.get(
    "/",
    response_model=List[OrganizationResponse],
    status_code=status.HTTP_200_OK,
)
async def get_my_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
):
    org_service = OrganizationService(db)
    return await org_service.get_user_organizations(user_id=current_user.id)


# 3. Get Single Organization Details
@router.get(
    "/{org_id}",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_organization_by_id(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
):
    org_service = OrganizationService(db)
    return await org_service.get_organization_details(
        org_id=org_id, user_id=current_user.id
    )


# 4. Update Organization Details
@router.patch(
    "/{org_id}",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
)
async def update_organization(
    org_id: uuid.UUID,
    payload: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
):
    org_service = OrganizationService(db)
    return await org_service.update_organization_details(
        org_id=org_id, payload=payload, user_id=current_user.id
    )


# 5. Delete Organization
@router.delete(
    "/{org_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_organization(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
):
    org_service = OrganizationService(db)
    await org_service.delete_organization(org_id=org_id, user_id=current_user.id)
    return None
