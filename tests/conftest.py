import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.database import get_db
from src.core.security import get_password_hash, is_authenticated
from src.main import app

# Test engine create karte waqt poolclass=NullPool pass karein


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Har test ke baad dependency overrides ko safely clear karein."""
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(mock_db_session):
    """Provides a fresh async client for testing public API routes with mocked DB session."""
    if hasattr(app, "dependency_overrides"):
        app.dependency_overrides[get_db] = lambda: mock_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def mock_user():
    """Provides a dummy authenticated user object with required schema attributes."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "testuser@example.com"
    user.full_name = "Test User"
    user.role = "Super Admin"
    user.is_active = True
    return user


@pytest_asyncio.fixture
async def mock_db_session():
    session = AsyncMock()

    default_mock_user = MagicMock()
    default_mock_user.id = uuid.uuid4()
    default_mock_user.email = "loginuser@example.com"
    default_mock_user.full_name = "Login User"
    # Generate a valid hash using your project's security utility
    default_mock_user.hashed_password = get_password_hash("StrongPassword123!")
    default_mock_user.is_active = True
    default_mock_user.is_superuser = False

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalars.return_value.first.return_value = default_mock_user
    mock_result.scalar_one_or_none.return_value = default_mock_user
    session.execute.return_value = mock_result

    def side_effect_add(instance):
        if hasattr(instance, "id") and not instance.id:
            instance.id = uuid.uuid4()
        if hasattr(instance, "is_active") and instance.is_active is None:
            instance.is_active = True
        if hasattr(instance, "is_superuser") and instance.is_superuser is None:
            instance.is_superuser = False

    session.add.side_effect = side_effect_add

    async def side_effect_refresh(instance):
        side_effect_add(instance)

    session.refresh.side_effect = side_effect_refresh

    return session


@pytest_asyncio.fixture
async def auth_client(mock_user, mock_db_session):
    """Provides an authenticated AsyncClient with X-Organization-Id header and mocked DB session."""
    app.dependency_overrides[is_authenticated] = lambda: mock_user

    if hasattr(app, "dependency_overrides"):
        app.dependency_overrides[get_db] = lambda: mock_db_session

    dummy_org_id = str(uuid.uuid4())
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Organization-Id": dummy_org_id},
    ) as ac:
        yield ac
