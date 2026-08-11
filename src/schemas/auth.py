import uuid

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserResponseSchema(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None = None
    is_active: bool
    is_superuser: bool

    model_config = ConfigDict(from_attributes=True)


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


# 👈 Added: Login aur Refresh endpoints ki token response ke liye
class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# 👈 Added: Refresh Token Endpoint Request payload ke liye
class RefreshTokenSchema(BaseModel):
    refresh_token: str
