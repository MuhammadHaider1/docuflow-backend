import asyncio

from sqlalchemy import text

from src.core.database import SessionLocal, engine
from src.core.seeding import seed_all_rbac
from src.models.base import Base


async def enable_vector_extension() -> None:
    """Enable pgvector in its own transaction.

    ``documentchunk.embedding`` is a ``vector(384)`` column, so the type has to
    exist first. It is committed separately on purpose: if it shared a
    transaction with the CREATE TABLE statements, any later failure would roll
    the extension back too, leaving a database that can never be created again
    without manual intervention.
    """
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


async def main():
    await enable_vector_extension()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ All database tables created successfully!")

    async with SessionLocal() as session:
        await seed_all_rbac(session)


if __name__ == "__main__":
    asyncio.run(main())
