import uuid
from typing import List

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import PermissionChecker
from src.core.database import get_db
from src.core.security import is_authenticated
from src.models.auth import User
from src.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from src.services.comment import CommentService

router = APIRouter(prefix="/comments", tags=["Comments"])


@router.post(
    "/documents/{document_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    document_id: uuid.UUID,
    payload: CommentCreate,
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("document:read")),
):
    service = CommentService(db)
    return await service.add_comment(
        document_id=document_id,
        user_id=current_user.id,
        org_id=x_organization_id,
        payload=payload,
    )


@router.get(
    "/documents/{document_id}/comments",
    response_model=List[CommentResponse],
    status_code=status.HTTP_200_OK,
)
async def get_document_comments(
    doc_id: uuid.UUID,
    x_organization_id: uuid.UUID = Header(..., alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
    _: bool = Depends(PermissionChecker("document:read")),
):
    service = CommentService(db)
    return await service.get_document_comments(
        document_id=doc_id, org_id=x_organization_id
    )


@router.patch(
    "/{comment_id}",
    response_model=CommentResponse,
    status_code=status.HTTP_200_OK,
)
async def update_comment(
    comment_id: uuid.UUID,
    payload: CommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
):
    service = CommentService(db)
    return await service.update_comment(
        comment_id=comment_id,
        current_user_id=current_user.id,
        payload=payload,
    )


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(is_authenticated),
):
    service = CommentService(db)
    await service.delete_comment(comment_id=comment_id, current_user_id=current_user.id)
    return None
