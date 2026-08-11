import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin


class Permission(Base, TimestampMixin):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    description: Mapped[str] = mapped_column(String(512), nullable=True)

    # Relationship to Role (Many to Many)
    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary="rolepermission", back_populates="permissions"
    )


class Role(Base, TimestampMixin):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=True)

    # Is role ke belongs to a specific tenant/organization.
    # Global roles (like super-admin) ke liye organization_id NULL ho sakti hai.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Relationships
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary="rolepermission", back_populates="roles"
    )

    __table_args__ = (
        UniqueConstraint(
            "name", "organization_id", name="uq_role_name_per_organization"
        ),
    )


class RolePermission(Base):
    """
    (Many-to-Many) between Roles and Permissions
    """

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("role.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permission.id", ondelete="CASCADE"),
        primary_key=True,
    )
