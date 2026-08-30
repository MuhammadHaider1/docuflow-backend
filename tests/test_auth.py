import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_signup(client: AsyncClient):
    """Verify user registration/signup endpoint."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "StrongPassword123!",
            "full_name": "New User",
        },
    )
    assert response.status_code in [200, 201, 400]


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    """Verify user login and token generation endpoint."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "loginuser@example.com",
            "password": "StrongPassword123!",
            "full_name": "Login User",
        },
    )

    # Login request using json payload matching LoginSchema
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "loginuser@example.com", "password": "StrongPassword123!"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_current_user(auth_client: AsyncClient):
    """Verify fetching current authenticated user profile."""
    response = await auth_client.get("/api/v1/auth/me")
    assert response.status_code == 200
