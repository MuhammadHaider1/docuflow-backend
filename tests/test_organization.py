import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from src.schemas.organization import OrganizationCreate
from src.services.organization import OWNER_ROLE_NAME, OrganizationService


@pytest.mark.asyncio
async def test_create_organization_returns_201(auth_client: AsyncClient, db_session):
    response = await auth_client.post(
        "/api/v1/organizations/",
        json={"name": "Test Tech Corp", "slug": "test-tech-corp"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Test Tech Corp"
    assert body["slug"] == "test-tech-corp"
    assert body["is_active"] is True
    assert db_session.commits >= 1


@pytest.mark.asyncio
async def test_create_organization_requires_authentication(client: AsyncClient):
    response = await client.post(
        "/api/v1/organizations/", json={"name": "Nope", "slug": "nope"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_organization_rejects_duplicate_slug(
    auth_client: AsyncClient, db_session, install_session
):
    """A second organization with the same slug must be a 400, not a silent success."""
    from src.models.organization import Organization

    from tests.conftest import FakeSession

    existing = Organization(id=uuid.uuid4(), name="Taken", slug="test-tech-corp")
    FakeSession._backfill(existing)
    session = FakeSession(
        user=db_session.user, org_id=db_session.org_id, documents=db_session.documents
    )
    original_execute = session.execute

    async def execute(stmt):
        result = await original_execute(stmt)
        if "Organization" in session._entities(stmt):
            return type(result)(scalars=[existing])
        return result

    session.execute = execute
    install_session(session)
    response = await auth_client.post(
        "/api/v1/organizations/",
        json={"name": "Test Tech Corp", "slug": "test-tech-corp"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Slug is already in use, please try a different one."
    )


@pytest.mark.asyncio
async def test_list_organizations_redirects_to_canonical_path(
    auth_client: AsyncClient,
):
    """The collection lives at the trailing-slash path; the bare one redirects."""
    response = await auth_client.get("/api/v1/organizations")
    assert response.status_code == 307
    assert response.headers["location"].endswith("/api/v1/organizations/")


@pytest.mark.asyncio
async def test_list_organizations_returns_list(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/organizations/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_organizations_requires_authentication(client: AsyncClient):
    response = await client.get("/api/v1/organizations/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_organization_requires_authentication(client: AsyncClient):
    response = await client.get(f"/api/v1/organizations/{uuid.uuid4()}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_organization_rejects_non_uuid(client: AsyncClient):
    """Shape validation happens before the auth dependency is exercised."""
    response = await client.get("/api/v1/organizations/not-a-uuid")
    assert response.status_code in (401, 422)


@pytest.mark.asyncio
async def test_unknown_organization_is_404(
    auth_client: AsyncClient, empty_db_session, install_session
):
    install_session(empty_db_session)
    response = await auth_client.get(f"/api/v1/organizations/{uuid.uuid4()}")
    assert response.status_code == 404


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
async def test_org_creation_never_falls_back_to_viewer():
    """Regression guard: the role lookup must not silently resolve to Viewer."""
    service = _service_with_repos()
    service.org_repo.get_by_slug.return_value = None
    service.user_repo.get_role_by_name.return_value = None

    with pytest.raises(HTTPException):
        await service.register_new_organization(
            OrganizationCreate(name="Acme", slug="acme"), uuid.uuid4()
        )

    requested = {
        call.args[0] for call in service.user_repo.get_role_by_name.await_args_list
    }
    assert requested == {OWNER_ROLE_NAME}
    assert "Viewer" not in requested
    service.org_repo.create.assert_not_awaited()


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


@pytest.mark.asyncio
async def test_duplicate_slug_is_rejected_before_creating():
    service = _service_with_repos()
    service.org_repo.get_by_slug.return_value = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await service.register_new_organization(
            OrganizationCreate(name="Acme", slug="acme"), uuid.uuid4()
        )

    assert exc_info.value.status_code == 400
    service.org_repo.create.assert_not_awaited()
    service.user_repo.get_role_by_name.assert_not_awaited()
