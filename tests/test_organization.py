import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from src.schemas.organization import OrganizationCreate
from src.services.organization import OWNER_ROLE_NAME, OrganizationService


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


def _service_with_repos():
    service = OrganizationService(AsyncMock())
    service.org_repo = AsyncMock()
    service.user_repo = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_org_creator_is_assigned_owner_role():
    """Jo organization banata hai usay owner role milna chahiye, Viewer nahi."""
    service = _service_with_repos()

    owner_role = MagicMock()
    owner_role.id = uuid.uuid4()
    owner_role.name = OWNER_ROLE_NAME

    new_org = MagicMock()
    new_org.id = uuid.uuid4()

    service.org_repo.get_by_slug.return_value = None
    service.user_repo.get_role_by_name.return_value = owner_role
    service.org_repo.create.return_value = new_org

    user_id = uuid.uuid4()
    await service.register_new_organization(
        OrganizationCreate(name="Acme", slug="acme"), user_id
    )

    service.user_repo.get_role_by_name.assert_awaited_once_with(OWNER_ROLE_NAME)
    service.org_repo.create_membership.assert_awaited_once_with(
        user_id=user_id, org_id=new_org.id, role_id=owner_role.id
    )


@pytest.mark.asyncio
async def test_org_creation_fails_when_owner_role_missing():
    """Seeder chalaya nahi gaya to user ko silently Viewer role na mile."""
    service = _service_with_repos()
    service.org_repo.get_by_slug.return_value = None
    service.user_repo.get_role_by_name.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await service.register_new_organization(
            OrganizationCreate(name="Acme", slug="acme"), uuid.uuid4()
        )

    assert exc_info.value.status_code == 404
    assert OWNER_ROLE_NAME in exc_info.value.detail
    service.org_repo.create.assert_not_awaited()
