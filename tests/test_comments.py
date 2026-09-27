import uuid

import pytest
from httpx import AsyncClient

from src.core.database import get_db
from src.main import app


@pytest.mark.asyncio
async def test_document_comments_require_authentication(client: AsyncClient):
    response = await client.get(
        f"/api/v1/comments/documents/{uuid.uuid4()}/comments"
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_create_comment_requires_authentication(client: AsyncClient):
    document_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/comments/documents/{document_id}/comments",
        json={"content": "Test comment"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_list_document_comments_returns_list(auth_client: AsyncClient):
    document_id = uuid.uuid4()
    response = await auth_client.get(
        f"/api/v1/comments/documents/{document_id}/comments"
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_comment_persists_and_returns_201(
    auth_client: AsyncClient, db_session, sample_document
):
    response = await auth_client.post(
        f"/api/v1/comments/documents/{sample_document.id}/comments",
        json={"content": "Why did we pick pgvector?"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["content"] == "Why did we pick pgvector?"
    assert body["document_id"] == str(sample_document.id)
    assert db_session.commits == 1


@pytest.mark.asyncio
async def test_create_comment_rejects_missing_content(auth_client: AsyncClient):
    """Omitting ``content`` must be a 422 from pydantic, not a 500."""
    document_id = uuid.uuid4()
    response = await auth_client.post(
        f"/api/v1/comments/documents/{document_id}/comments", json={}
    )
    assert response.status_code == 422
    errors = {e["loc"][-1] for e in response.json()["detail"]}
    assert "content" in errors


@pytest.mark.asyncio
async def test_list_comments_rejects_non_uuid_document_id(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/comments/documents/not-a-uuid/comments")
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "uuid_parsing"


@pytest.mark.asyncio
async def test_comments_are_tenant_isolated(
    auth_client: AsyncClient, empty_db_session, foreign_document
):
    """A document from another organization must be invisible (404, not 403).

    Returning 403 would confirm the document exists; 404 keeps the tenant's
    document ids unguessable.
    """
    app.dependency_overrides[get_db] = lambda: empty_db_session
    response = await auth_client.get(
        f"/api/v1/comments/documents/{foreign_document.id}/comments"
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found in this organization"


@pytest.mark.asyncio
async def test_create_comment_on_foreign_document_is_404(
    auth_client: AsyncClient, empty_db_session, foreign_document
):
    app.dependency_overrides[get_db] = lambda: empty_db_session
    response = await auth_client.post(
        f"/api/v1/comments/documents/{foreign_document.id}/comments",
        json={"content": "should not be accepted"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found in this organization"
