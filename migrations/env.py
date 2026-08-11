import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# 🚨 SAARE MODEL MODULES KO IMPORT KAREIN (Taki SQLAlchemy Registry activate rahe)
import src.models.auth
import src.models.document
import src.models.organization
import src.models.rbac

# Core settings aur Base models
from src.core.config import settings
from src.core.database import Base

# Explicit class imports (Double guarantee for metadata linkage)
from src.models.auth import RefreshToken, User
from src.models.comment import Comment
from src.models.document import Document, DocumentVersion, Folder
from src.models.organization import Membership, Organization
from src.models.rbac import Permission, Role, RolePermission

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Strictly get the correct asynchronous URL from settings control center"""
    return str(settings.DATABASE_URI)


# 🔒 Non-application / External tables ko touch karne se rokne ke liye filter
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and (
        name.startswith("django_")
        or name.startswith("accounts_")
        or name.startswith("auth_")
    ):
        return False  # In tables ko completely ignore kar do
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode (Asynchronous)."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
