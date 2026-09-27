import uuid
from io import BytesIO

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_document_search_requires_authentication(client: AsyncClient):
    response = await client.get("/api/v1/documents/search")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_document_search_requires_org_header(auth_client: AsyncClient):
    """Without X-Organization-Id the request is a 422, never a cross-tenant read."""
    response = await auth_client.get(
        "/api/v1/documents/search", headers={"X-Organization-Id": ""}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_document_search_returns_paginated_payload(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/documents/search")
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"items", "total", "page", "page_size", "total_pages"}
    assert body["page"] == 1
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["title"] == "Architecture Decision Record"


@pytest.mark.asyncio
async def test_document_search_rejects_invalid_sort_column(auth_client: AsyncClient):
    response = await auth_client.get(
        "/api/v1/documents/search", params={"sort_by": "title; DROP TABLE documents"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_document_search_rejects_page_size_over_limit(auth_client: AsyncClient):
    response = await auth_client.get(
        "/api/v1/documents/search", params={"page_size": 500}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_requires_authentication(client: AsyncClient):
    files = {"file": ("t.pdf", BytesIO(b"%PDF-1.4"), "application/pdf")}
    response = await client.post("/api/v1/documents", files=files, data={"title": "T"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_requires_a_file(auth_client: AsyncClient):
    """No file part at all must fail validation before any storage call."""
    response = await auth_client.post("/api/v1/documents", data={"title": "No file"})
    assert response.status_code == 422
    errors = {e["loc"][-1] for e in response.json()["detail"]}
    assert "file" in errors


@pytest.mark.asyncio
async def test_upload_requires_title(auth_client: AsyncClient):
    files = {"file": ("t.pdf", BytesIO(b"%PDF-1.4"), "application/pdf")}
    response = await auth_client.post("/api/v1/documents", files=files, data={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_folder_tree_returns_list(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/folders/tree")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_folder_returns_201(auth_client: AsyncClient, db_session):
    response = await auth_client.post("/api/v1/folders", json={"name": "Design Docs"})
    assert response.status_code == 201, response.text
    assert response.json()["name"] == "Design Docs"


@pytest.mark.asyncio
async def test_create_folder_rejects_empty_name(auth_client: AsyncClient):
    response = await auth_client.post("/api/v1/folders", json={"name": ""})
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_document_details_rejects_non_uuid(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/documents/not-a-uuid")
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "uuid_parsing"


@pytest.mark.asyncio
async def test_delete_document_from_other_tenant_is_404(
    auth_client: AsyncClient, empty_db_session, foreign_document, install_session
):
    """Cross-tenant deletion must be indistinguishable from a missing document."""
    install_session(empty_db_session)
    response = await auth_client.delete(f"/api/v1/documents/{foreign_document.id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unknown_document_id_is_404(
    auth_client: AsyncClient, empty_db_session, install_session
):
    install_session(empty_db_session)
    response = await auth_client.get(f"/api/v1/documents/{uuid.uuid4()}")
    assert response.status_code == 404
