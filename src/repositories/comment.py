import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.comment import Comment
from src.schemas.comment import CommentCreate, CommentUpdate


class CommentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_comment(
        self, doc_id: uuid.UUID, user_id: uuid.UUID, obj_in: CommentCreate
    ) -> Comment:
        db_obj = Comment(
            content=obj_in.content,
            parent_id=obj_in.parent_id,
            document_id=doc_id,
            user_id=user_id,
        )

        self.db.add(db_obj)
        await self.db.flush()

        # Eager load user for response schema consistency
        await self.db.refresh(db_obj, attribute_names=["user"])
        return db_obj

    async def get_document_root_comment(self, doc_id: uuid.UUID):
        stmt = (
            select(Comment)
            .where(
                Comment.document_id == doc_id,
                Comment.parent_id.is_(None),  # Sirf root comments
            )
            .options(
                selectinload(Comment.user),
                selectinload(Comment.replies).selectinload(Comment.user),
                selectinload(Comment.replies)
                .selectinload(Comment.replies)
                .selectinload(Comment.user),
            )
            .order_by(Comment.created_at.asc())  # Oldest first
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_comment_by_id(self, comment_id: uuid.UUID) -> Comment | None:
        stmt = (
            select(Comment)
            .where(Comment.id == comment_id)
            .options(selectinload(Comment.user))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_comment(self, comment: Comment, obj_in: CommentUpdate) -> Comment:
        comment.content = obj_in.content
        await self.db.flush()
        await self.db.refresh(comment, attribute_names=["user"])
        return comment

    async def delete_comment(self, comment_id: uuid.UUID) -> bool:
        comment = await self.get_comment_by_id(comment_id)
        if not comment:
            return False

        await self.db.delete(comment)
        await self.db.flush()
        return True
