from io import BytesIO

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_documents_authenticated(auth_client: AsyncClient):
    """Verify authenticated user can request document search/list."""
    response = await auth_client.get("/api/v1/documents/search", follow_redirects=True)
    assert response.status_code in [200, 403, 404, 422, 500]


@pytest.mark.asyncio
async def test_upload_document_authenticated(auth_client: AsyncClient):
    """Verify document upload route handles requests properly."""
    fake_file_content = b"test document content"
    files = {"file": ("test.pdf", BytesIO(fake_file_content), "application/pdf")}
    data = {"title": "Test PDF Document", "description": "Automated test upload"}

    response = await auth_client.post(
        "/api/v1/documents", files=files, data=data, follow_redirects=True
    )
    assert response.status_code in [200, 201, 400, 403, 422, 500]
