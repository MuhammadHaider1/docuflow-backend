import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_audit_logs_require_authentication(client: AsyncClient):
    """Audit logs must never be readable without a bearer token."""
    response = await client.get(
        "/api/v1/audit-logs/", params={"organization_id": str(uuid.uuid4())}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_audit_logs_returns_list_for_authenticated_member(
    auth_client: AsyncClient,
):
    response = await auth_client.get(
        "/api/v1/audit-logs/", params={"organization_id": str(uuid.uuid4())}
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_audit_logs_requires_organization_id_query_param(
    auth_client: AsyncClient,
):
    """Omitting organization_id is a 422, not a silent 200."""
    response = await auth_client.get("/api/v1/audit-logs/")
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert errors[0]["loc"] == ["query", "organization_id"]


@pytest.mark.asyncio
async def test_audit_logs_rejects_malformed_organization_id(
    auth_client: AsyncClient,
):
    response = await auth_client.get(
        "/api/v1/audit-logs/", params={"organization_id": "not-a-uuid"}
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "uuid_parsing"
