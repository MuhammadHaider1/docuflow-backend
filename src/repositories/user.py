import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.auth import User
from src.models.rbac import Role
from src.schemas.auth import UserCreate


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, obj_in: UserCreate, hashed_password: str) -> User:
        db_obj = User(
            email=obj_in.email,
            full_name=obj_in.full_name,
            hashed_password=hashed_password,
        )

        self.db.add(db_obj)
        await self.db.flush()
        return db_obj

    async def get_by_email(self, user_email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == user_email))
        return result.scalar_one_or_none()

    # 👈 Added: Refresh token / Auth middleware verification ke liye zaroori function
    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_role_by_name(self, role_name: str) -> Role | None:
        query = select(Role).where(Role.name == role_name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
