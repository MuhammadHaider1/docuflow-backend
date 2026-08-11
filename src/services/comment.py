import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.comment import CommentRepository
from src.repositories.document import DocumentRepository
from src.schemas.comment import CommentCreate, CommentUpdate


class CommentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.comment_repo = CommentRepository(db)
        self.document_repo = DocumentRepository(db)

    async def add_comment(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        payload: CommentCreate,
    ):
        # 1. Verify Document & Multi-tenant isolation
        doc = await self.document_repo.get_document_by_id(document_id)
        if not doc or doc.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found in this organization",
            )

        # 2. Verify Parent Comment (if it's a reply)
        if payload.parent_id is not None:
            parent = await self.comment_repo.get_comment_by_id(payload.parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent comment not found",
                )

            # Check if parent comment belongs to the same document
            if parent.document_id != document_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent comment belongs to another document",
                )

        # 3. Create & Persist Comment
        comment = await self.comment_repo.create_comment(document_id, user_id, payload)
        await self.db.commit()

        # Re-fetch full object with eager loaded relationship for Pydantic schema
        return await self.comment_repo.get_comment_by_id(comment.id)

    async def get_document_comments(self, document_id: uuid.UUID, org_id: uuid.UUID):
        # 1. Verify Document & Multi-tenant isolation
        doc = await self.document_repo.get_document_by_id(document_id)
        if not doc or doc.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found in this organization",
            )

        # 2. Fetch Root Comments with Nested Replies
        return await self.comment_repo.get_document_root_comment(document_id)

    async def update_comment(
        self,
        comment_id: uuid.UUID,
        current_user_id: uuid.UUID,
        payload: CommentUpdate,
    ):
        comment = await self.comment_repo.get_comment_by_id(comment_id)
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
            )

        # Ownership check
        if comment.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to edit this comment",
            )

        updated_comment = await self.comment_repo.update_comment(comment, payload)
        await self.db.commit()
        return updated_comment

    async def delete_comment(self, comment_id: uuid.UUID, current_user_id: uuid.UUID):
        comment = await self.comment_repo.get_comment_by_id(comment_id)
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
            )

        # Ownership check
        if comment.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this comment",
            )

        await self.comment_repo.delete_comment(comment_id)
        await self.db.commit()
