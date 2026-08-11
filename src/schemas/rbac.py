import uuid

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------
# PERMISSION SCHEMAS
# ------------------------------------------
class PermissionRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------
# ROLE SCHEMAS
# ------------------------------------------
class RoleCreateUpdate(BaseModel):
    name: str
    description: str | None = None
    permission_ids: list[uuid.UUID] = []


class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    organization_id: uuid.UUID | None = None
    permissions: list[PermissionRead] = []

    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------
# ASSIGNMENT SCHEMAS
# ------------------------------------------


class AssignRoleRequest(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID = Field(
        ..., description="The ID of the role to assign to the user"
    )


class RevokeRoleRequest(BaseModel):
    user_id: uuid.UUID
