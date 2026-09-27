import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128


def validate_password_strength(value: str) -> str:
    """Reject passwords that would be trivially guessable.

    A 2019 offline-cracked list of the most common passwords plus a tiny
    character set is not a meaningful secret, so length is required and a
    small set of well-known passwords is refused outright.
    """
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
        )
    if len(value) > MAX_PASSWORD_LENGTH:
        # bcrypt silently truncates beyond 72 bytes, which would make two
        # different passwords equivalent.
        raise ValueError(
            f"Password must be at most {MAX_PASSWORD_LENGTH} characters long."
        )
    if value.lower() in COMMON_PASSWORDS:
        raise ValueError("This password is too common, please choose another one.")
    return value


COMMON_PASSWORDS = frozenset(
    {
        "password",
        "password1",
        "password123",
        "passw0rd",
        "12345678",
        "123456789",
        "1234567890",
        "12345678901",
        "123456789012",
        "qwerty12345",
        "qwertyuiop",
        "iloveyou12",
        "admin12345",
        "administrator",
        "letmein123",
        "welcome123",
        "docuflow123",
        "user123456",
    }
)


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def _check_strength(cls, value: str) -> str:
        return validate_password_strength(value)


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
