"""add recovery escalation notes

Revision ID: 5678290fd7e6
Revises: 540169978698
Create Date: 2026-09-04 17:08:42.668742

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5678290fd7e6"
down_revision: Union[str, Sequence[str], None] = "540169978698"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "recovery_escalation_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.String(length=255), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_recovery_escalation_notes_case_id",
        "recovery_escalation_notes",
        ["case_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_recovery_escalation_notes_case_id",
        table_name="recovery_escalation_notes",
    )
    op.drop_table("recovery_escalation_notes")