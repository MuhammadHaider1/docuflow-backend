import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.organization import Organization


class Folder(Base, TimestampMixin):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(50), nullable=False)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("folder.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # 🔗 Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    subfolders: Mapped[list["Folder"]] = relationship(
        "Folder", back_populates="parent_folder", cascade="all, delete-orphan"
    )
    parent_folder: Mapped["Folder | None"] = relationship(
        "Folder", remote_side=[id], back_populates="subfolders"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="folder", cascade="all, delete-orphan"
    )


class Document(Base, TimestampMixin):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("folder.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )

    processing_status: Mapped[str] = mapped_column(String(50), default="pending")
    is_archived: Mapped[bool] = mapped_column(default=False, nullable=False)

    # 🌟 NEW: OCR / Extracted PDF Content Column
    extracted_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 🔗 Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="documents"
    )
    folder: Mapped["Folder"] = relationship("Folder", back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship(
        "DocumentVersion", back_populates="document", cascade="all, delete-orphan"
    )

    comment = relationship(
        "Comment", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentVersion(Base, TimestampMixin):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )

    # 🔗 Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="versions")
