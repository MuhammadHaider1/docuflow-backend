import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.audit import AuditLog
    from src.models.auth import User
    from src.models.document import Document
    from src.models.rbac import Role


class Organization(Base, TimestampMixin):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # 🔗 Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="membership",
        back_populates="organizations",
        overlaps="memberships",
    )
    memberships: Mapped[list["Membership"]] = relationship(
        "Membership",
        back_populates="organization",
        cascade="all, delete-orphan",
        overlaps="organizations,users",
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="organization", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="organization"
    )


class Membership(Base, TimestampMixin):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("role.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="memberships", overlaps="organizations,users"
    )
    user: Mapped["User"] = relationship(
        "User", back_populates="memberships", overlaps="organizations,users"
    )
    role: Mapped[Optional["Role"]] = relationship("Role")
