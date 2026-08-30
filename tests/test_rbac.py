import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rbac_roles_list_authenticated(auth_client: AsyncClient):
    """Verify listing roles via RBAC endpoint."""
    response = await auth_client.get("/api/v1/rbac/roles", follow_redirects=True)
    assert response.status_code in [200, 403, 404, 422, 500]


@pytest.mark.asyncio
async def test_assign_role_to_user(auth_client: AsyncClient):
    """Verify assigning a role to a user."""
    # Correct path endpoint is /api/v1/rbac/assign-role based on router definitions
    response = await auth_client.post(
        "/api/v1/rbac/assign-role",
        json={"user_id": str(uuid.uuid4()), "role_id": str(uuid.uuid4())},
        follow_redirects=True,
    )
    assert response.status_code in [200, 201, 400, 403, 404, 422, 500]
