import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from src.models.notification import Notification


def _notification(user_id: uuid.UUID, is_read: bool = False) -> Notification:
    return Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        title="Document ready",
        message="Your document finished processing",
        notification_type="document",
        is_read=is_read,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_list_notifications_requires_authentication(client: AsyncClient):
    response = await client.get("/api/v1/notifications/")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_mark_read_requires_authentication(client: AsyncClient):
    response = await client.patch(f"/api/v1/notifications/{uuid.uuid4()}/read")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_mark_all_read_requires_authentication(client: AsyncClient):
    response = await client.post("/api/v1/notifications/read-all")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_notifications_returns_empty_list(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/notifications/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_notifications_rejects_limit_over_max(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/notifications/", params={"limit": 500})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_notifications_rejects_negative_offset(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/notifications/", params={"offset": -1})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_mark_read_returns_404_for_unknown_id(auth_client: AsyncClient):
    response = await auth_client.patch(f"/api/v1/notifications/{uuid.uuid4()}/read")
    assert response.status_code == 404
    assert response.json()["detail"] == "Notification not found or access denied"


@pytest.mark.asyncio
async def test_mark_read_rejects_non_uuid_id(auth_client: AsyncClient):
    response = await auth_client.patch("/api/v1/notifications/1/read")
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "uuid_parsing"


@pytest.mark.asyncio
async def test_mark_all_read_returns_count(auth_client: AsyncClient, db_session):
    response = await auth_client.post("/api/v1/notifications/read-all")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["updated_count"] == 0
    assert "message" in body


@pytest.mark.asyncio
async def test_mark_all_read_reports_updated_rows(
    auth_client: AsyncClient, db_session, install_session
):
    """A non-zero rowcount must be reported back, not silently dropped."""
    original = db_session.execute

    async def execute(stmt):
        result = await original(stmt)
        result.rowcount = 4
        return result

    db_session.execute = execute
    install_session(db_session)
    response = await auth_client.post("/api/v1/notifications/read-all")
    assert response.status_code == 200
    assert response.json()["updated_count"] == 4
    assert "4" in response.json()["message"]


@pytest.mark.asyncio
async def test_mark_read_flips_own_notification(auth_client: AsyncClient, db_session):
    """The happy path must actually persist is_read=True."""
    mine = _notification(db_session.user.id, is_read=False)
    db_session.notifications = [mine]
    response = await auth_client.patch(f"/api/v1/notifications/{mine.id}/read")
    assert response.status_code == 200, response.text
    assert response.json()["is_read"] is True
    assert mine.is_read is True


@pytest.mark.asyncio
async def test_other_users_notification_cannot_be_marked_read(
    auth_client: AsyncClient, db_session
):
    """Another member's notification must 404 and stay unread."""
    other = _notification(uuid.uuid4(), is_read=False)
    db_session.notifications = [other]
    response = await auth_client.patch(f"/api/v1/notifications/{other.id}/read")
    assert response.status_code == 404
    assert other.is_read is False
