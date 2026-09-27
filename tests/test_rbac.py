"""RBAC tests that exercise the real ``PermissionChecker``.

Every other test module relies on the member being a ``Super Admin`` so route
behaviour is reachable.  This module varies the member's role and permissions to
prove the checker actually denies access — the failure mode that let the
``Viewer``/``Organization Owner`` bug ship unnoticed.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.database import get_db
from src.core.security import is_authenticated
from src.main import app
from tests.conftest import FakeSession, _make_user


async def _client_for(session: FakeSession) -> AsyncClient:
    """Build an authenticated client whose permission checks run for real."""
    app.dependency_overrides[is_authenticated] = lambda: session.user
    app.dependency_overrides[get_db] = lambda: session
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Organization-Id": str(session.org_id)},
    )


@pytest.fixture
def member_factory(org_id):
    """Build a session for a member with an explicit role and permission set."""

    def _make(role_name: str, permissions: tuple[str, ...] = ()):
        user = _make_user(
            f"{role_name.lower().replace(' ', '.')}@example.com", role_name, "x"
        )
        return FakeSession(
            user=user, org_id=org_id, role_name=role_name, permissions=permissions
        )

    return _make


@pytest.mark.asyncio
async def test_list_roles_requires_authentication(client: AsyncClient):
    response = await client.get("/api/v1/rbac/roles")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_super_admin_may_assign_roles(member_factory):
    session = member_factory("Super Admin", ("members:manage_roles",))
    async with await _client_for(session) as ac:
        response = await ac.post(
            "/api/v1/rbac/assign-role",
            json={"user_id": str(uuid.uuid4()), "role_id": str(session.role.id)},
        )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_organization_owner_may_assign_roles(member_factory):
    """The role the organization-creator bug assigned must be able to manage roles."""
    session = member_factory("Organization Owner", ())
    async with await _client_for(session) as ac:
        response = await ac.post(
            "/api/v1/rbac/assign-role",
            json={"user_id": str(uuid.uuid4()), "role_id": str(session.role.id)},
        )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_viewer_is_denied_role_management(member_factory):
    session = member_factory("Viewer", ())
    async with await _client_for(session) as ac:
        response = await ac.post(
            "/api/v1/rbac/assign-role",
            json={"user_id": str(uuid.uuid4()), "role_id": str(session.role.id)},
        )
    assert response.status_code == 403
    assert "members:manage_roles" in response.json()["detail"]


@pytest.mark.asyncio
async def test_viewer_with_unrelated_permission_is_still_denied(member_factory):
    """Having *a* permission must not grant a different one."""
    session = member_factory("Viewer", ("document:read",))
    async with await _client_for(session) as ac:
        response = await ac.post(
            "/api/v1/rbac/assign-role",
            json={"user_id": str(uuid.uuid4()), "role_id": str(session.role.id)},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_non_member_is_denied_entirely(org_id):
    """No membership row at all must be rejected, not treated as an empty grant."""
    user = _make_user("stranger@example.com", "Stranger", "x")
    session = FakeSession(
        user=user, org_id=org_id, role_name="Ghost", permissions=(), is_member=False
    )
    async with await _client_for(session) as ac:
        response = await ac.get(f"/api/v1/rbac/members/{user.id}/role")
    assert response.status_code == 403
    assert response.json()["detail"] == "User is not a member of this organization"


@pytest.mark.asyncio
async def test_editor_cannot_read_organization_audit_trail(member_factory):
    session = member_factory("Editor", ("document:create", "document:read"))
    async with await _client_for(session) as ac:
        response = await ac.get("/api/v1/rbac/members/{}/role".format(uuid.uuid4()))
    assert response.status_code == 403
    assert "organization:read" in response.json()["detail"]


@pytest.mark.asyncio
async def test_assign_role_requires_org_header(member_factory):
    """Without X-Organization-Id the role must never be changed."""
    session = member_factory("Super Admin", ("members:manage_roles",))
    app.dependency_overrides[is_authenticated] = lambda: session.user
    app.dependency_overrides[get_db] = lambda: session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/rbac/assign-role",
            json={"user_id": str(uuid.uuid4()), "role_id": str(session.role.id)},
        )
    assert response.status_code == 422
    errors = {e["loc"][-1] for e in response.json()["detail"]}
    assert "X-Organization-Id" in errors


@pytest.mark.asyncio
async def test_assign_role_rejects_malformed_uuids(member_factory):
    session = member_factory("Super Admin", ("members:manage_roles",))
    async with await _client_for(session) as ac:
        response = await ac.post(
            "/api/v1/rbac/assign-role",
            json={"user_id": "not-a-uuid", "role_id": "also-not-a-uuid"},
        )
    assert response.status_code == 422
    fields = {e["loc"][-1] for e in response.json()["detail"]}
    assert {"user_id", "role_id"} <= fields


@pytest.mark.asyncio
async def test_list_permissions_requires_authentication(client: AsyncClient):
    response = await client.get("/api/v1/rbac/permissions")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_revoke_role_requires_authentication(client: AsyncClient):
    response = await client.post(
        "/api/v1/rbac/revoke-role", json={"user_id": str(uuid.uuid4())}
    )
    assert response.status_code == 401
