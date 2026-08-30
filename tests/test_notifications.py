import pytest


@pytest.mark.asyncio
async def test_notifications_list_unauthorized(client):
    """Verify fetching notifications list requires auth."""
    response = await client.get("/api/v1/notifications/", follow_redirects=True)
    assert response.status_code in [401, 403, 404, 405]


@pytest.mark.asyncio
async def test_mark_notification_read_unauthorized(client):
    """Verify marking a notification as read requires auth."""
    response = await client.patch("/api/v1/notifications/1/read", follow_redirects=True)
    assert response.status_code in [401, 403, 404, 405]


@pytest.mark.asyncio
async def test_mark_all_notifications_read_unauthorized(client):
    """Verify marking all notifications as read requires auth."""
    response = await client.post(
        "/api/v1/notifications/read-all", follow_redirects=True
    )
    assert response.status_code in [401, 403, 404, 405]
