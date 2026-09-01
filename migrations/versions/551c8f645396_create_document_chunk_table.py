"""create_document_chunk_table

Revision ID: 551c8f645396
Revises: 58ec53cea992
Create Date: 2026-08-31 06:30:33.470538

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "551c8f645396"
down_revision: Union[str, Sequence[str], None] = "58ec53cea992"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Manual Table Creation
    op.create_table(
        "documentchunk",  # Class name based table name
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Index for fast lookup
    op.create_index(op.f("ix_documentchunk_id"), "documentchunk", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_documentchunk_id"), table_name="documentchunk")
    op.drop_table("documentchunk")
