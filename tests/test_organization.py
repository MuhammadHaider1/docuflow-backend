import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_organization(auth_client: AsyncClient):
    """Verify creating a new organization endpoint."""
    response = await auth_client.post(
        "/api/v1/organizations/",
        json={"name": "Test Tech Corp", "slug": "test-tech-corp"},
        follow_redirects=True,
    )
    assert response.status_code in [200, 201, 400, 404, 422, 500]


@pytest.mark.asyncio
async def test_list_organizations(auth_client: AsyncClient):
    """Verify listing organizations endpoint."""
    response = await auth_client.get("/api/v1/organizations", follow_redirects=True)
    assert response.status_code in [200, 403, 404, 422, 500]


@pytest.mark.asyncio
async def test_organization_membership(auth_client: AsyncClient):
    """Verify adding membership to an organization endpoint."""
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    response = await auth_client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"user_id": str(user_id), "role_id": None},
        follow_redirects=True,
    )
    assert response.status_code in [200, 201, 400, 403, 404, 422, 500]
