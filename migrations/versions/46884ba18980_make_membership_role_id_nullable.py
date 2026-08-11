"""make_membership_role_id_nullable

Revision ID: 46884ba18980
Revises: <KEEP_THE_GENERATED_HASH_HERE>
Create Date: 2026-07-23 18:55:44.065706

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "46884ba18980"
down_revision: Union[str, None] = "70fbb5138a2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Strictly make membership.role_id nullable without dropping any tables
    op.alter_column("membership", "role_id", existing_type=sa.UUID(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("membership", "role_id", existing_type=sa.UUID(), nullable=False)
