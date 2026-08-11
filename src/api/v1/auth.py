from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import is_authenticated
from src.models.auth import User
from src.schemas.auth import (
    LoginSchema,
    RefreshTokenSchema,
    TokenResponseSchema,
    UserCreate,
    UserResponseSchema,
)
from src.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    return await auth_service.register_new_user(payload)


@router.post(
    "/login",
    response_model=TokenResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def login_user_endpoint(payload: LoginSchema, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    return await auth_service.login_user(payload)


@router.post(
    "/refresh",
    response_model=TokenResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def refresh_token_endpoint(
    payload: RefreshTokenSchema, db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)
    return await auth_service.refresh_access_token(payload.refresh_token)


@router.get(
    "/me",
    response_model=UserResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_current_user_profile(
    current_user: User = Depends(is_authenticated),
):
    return current_user


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout_user_endpoint(
    current_user: User = Depends(is_authenticated),
):
    # Pure JWT setup mein response ok return hota hai,
    # client side access/refresh tokens clear kar diye jate hain.
    return {"detail": "Successfully logged out"}
