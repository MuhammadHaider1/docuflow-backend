import asyncio

from src.core.database import SessionLocal, engine
from src.core.seeding import seed_all_rbac
from src.models.base import Base


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ All database tables created successfully!")

    async with SessionLocal() as session:
        await seed_all_rbac(session)


if __name__ == "__main__":
    asyncio.run(main())
