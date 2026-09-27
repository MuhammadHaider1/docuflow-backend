import pytest
from httpx import AsyncClient

from pydantic import ValidationError

from src.core.security import create_access_token, create_refresh_token
from src.schemas.auth import UserCreate
from tests.conftest import LOGIN_PASSWORD


@pytest.mark.asyncio
async def test_register_returns_201_and_persists(
    client: AsyncClient, vacant_db_session, install_session
):
    install_session(vacant_db_session)
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": LOGIN_PASSWORD,
            "full_name": "New User",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "newuser@example.com"
    assert body["full_name"] == "New User"
    assert body["is_active"] is True
    # The password must never be echoed back.
    assert "hashed_password" not in body
    assert LOGIN_PASSWORD not in response.text
    assert len(vacant_db_session.users) == 1


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(
    client: AsyncClient, db_session, install_session
):
    install_session(db_session)
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": db_session.user.email,
            "password": LOGIN_PASSWORD,
            "full_name": "Impostor",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Email already in use, please try a different one"
    )


@pytest.mark.asyncio
async def test_register_rejects_invalid_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": LOGIN_PASSWORD},
    )
    assert response.status_code == 422
    errors = {e["loc"][-1] for e in response.json()["detail"]}
    assert "email" in errors


@pytest.mark.asyncio
async def test_login_returns_both_tokens(client: AsyncClient, login_db_session):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "loginuser@example.com", "password": LOGIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]
    assert body["access_token"] != body["refresh_token"]


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "loginuser@example.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    # The error must not reveal whether the email exists.
    assert response.json()["detail"] == "Invalid Email or Password"


@pytest.mark.asyncio
async def test_login_rejects_unknown_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": LOGIN_PASSWORD},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Email or Password"


@pytest.mark.asyncio
async def test_login_requires_both_fields(client: AsyncClient):
    response = await client.post("/api/v1/auth/login", json={"email": "a@b.com"})
    assert response.status_code == 422
    errors = {e["loc"][-1] for e in response.json()["detail"]}
    assert "password" in errors


@pytest.mark.asyncio
async def test_get_current_user_returns_profile(auth_client: AsyncClient, db_session):
    response = await auth_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(db_session.user.id)
    assert body["email"] == "testuser@example.com"
    assert "hashed_password" not in body


@pytest.mark.asyncio
async def test_get_current_user_requires_authentication(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_requires_authentication(client: AsyncClient):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_succeeds_for_authenticated_user(auth_client: AsyncClient):
    response = await auth_client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json()["detail"] == "Successfully logged out"


@pytest.mark.asyncio
async def test_refresh_token_returns_new_pair(
    client: AsyncClient, db_session, install_session
):
    install_session(db_session)
    token = create_refresh_token(subject=str(db_session.user.id))
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert response.status_code == 200, response.text
    assert response.json()["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_rejects_access_token(
    client: AsyncClient, db_session, install_session
):
    """An access token must not be usable at the refresh endpoint."""
    install_session(db_session)

    access = create_access_token(subject=str(db_session.user.id))
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"


@pytest.mark.asyncio
async def test_refresh_rejects_garbage_token(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "not-a-jwt"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_rejects_garbage_bearer_token(client: AsyncClient):
    """A syntactically present but invalid token must be rejected by is_authenticated."""
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"


@pytest.mark.parametrize(
    "weak",
    [
        "user1",
        "password",
        "password123",
        "12345678901",
        "docuflow123",
        "short",
        "a" * 200,
    ],
)
def test_weak_passwords_are_rejected(weak: str):
    """Registration must refuse guessable or over-long passwords."""
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", password=weak)


@pytest.mark.parametrize(
    "strong",
    [
        "correct-horse-battery-staple",
        "a-very-long-passphrase-2026",
    ],
)
def test_strong_passwords_are_accepted(strong: str):
    assert UserCreate(email="a@b.com", password=strong).password == strong


@pytest.mark.asyncio
async def test_register_endpoint_enforces_password_policy(
    client: AsyncClient, vacant_db_session, install_session
):
    install_session(vacant_db_session)
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "user1"},
    )
    assert response.status_code == 422
    assert any("at least" in e.get("msg", "") for e in response.json()["detail"])
