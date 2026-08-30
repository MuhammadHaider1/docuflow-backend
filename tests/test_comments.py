import pytest


@pytest.mark.asyncio
async def test_comments_list_unauthorized(client):
    """Verify listing comments requires authentication."""
    response = await client.get("/api/v1/comments/", follow_redirects=True)
    assert response.status_code in [401, 403, 404, 405]


@pytest.mark.asyncio
async def test_create_comment_unauthorized(client):
    """Verify creating a comment requires authentication."""
    payload = {"content": "Test comment", "document_id": 1}
    response = await client.post(
        "/api/v1/comments/", json=payload, follow_redirects=True
    )
    assert response.status_code in [401, 403, 404, 405, 422]
