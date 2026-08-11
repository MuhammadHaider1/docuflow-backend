import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.auth import User
from src.models.base import Base, TimestampMixin
from src.models.document import Document


class Comment(Base, TimestampMixin):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document.id", ondelete="CASCADE")
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE")
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comment.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # RELATIONSHIPS

    document: Mapped["Document"] = relationship(back_populates="comment")

    user: Mapped["User"] = relationship(back_populates="comments")

    # 3. Nested replies (Self-referencing relationship)
    replies: Mapped[list["Comment"]] = relationship(
        "Comment", cascade="all, delete-orphan", lazy="selectin"
    )
