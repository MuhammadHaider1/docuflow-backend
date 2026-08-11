import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# ==========================================
# ORGANIZATION SCHEMAS
# ==========================================


class OrganizationBase(BaseModel):
    name: str = Field(
        ..., min_length=2, max_length=100, description="Organization name"
    )
    slug: str = Field(
        ..., min_length=2, max_length=100, description="Unique slug for URL"
    )


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationResponse(OrganizationBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None


# ==========================================
# MEMBERSHIP SCHEMAS
# ==========================================


class MembershipBase(BaseModel):
    user_id: uuid.UUID
    organization_id: uuid.UUID
    role_id: Optional[uuid.UUID] = Field(
        default=None, description="Assigned RBAC role ID, optional"
    )


class MembershipCreate(BaseModel):
    user_id: uuid.UUID
    role_id: Optional[uuid.UUID] = None  # 👈 Optional for initial onboarding


class MembershipResponse(MembershipBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
