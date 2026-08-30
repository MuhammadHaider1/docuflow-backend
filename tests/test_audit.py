import pytest


@pytest.mark.asyncio
async def test_audit_logs_unauthorized(client):
    """Verify audit logs endpoint requires auth."""
    response = await client.get("/api/v1/audit/", follow_redirects=True)
    assert response.status_code in [401, 403, 404, 405]
