import asyncio
from src.core.database import engine
from src.models.base import Base
import src.models

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ All database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(main())
