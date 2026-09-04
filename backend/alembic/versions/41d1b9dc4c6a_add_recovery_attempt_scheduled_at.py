"""add recovery attempt scheduled at

Revision ID: 41d1b9dc4c6a
Revises: 075c12467686
Create Date: 2026-09-04 14:46:54.044177

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41d1b9dc4c6a'
down_revision: Union[str, Sequence[str], None] = '075c12467686'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "recovery_attempts",
        sa.Column(
            "scheduled_at",
            sa.DateTime(),
            nullable=True,
        ),
    )

    op.create_index(
        op.f("ix_recovery_attempts_scheduled_at"),
        "recovery_attempts",
        ["scheduled_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_recovery_attempts_scheduled_at"),
        table_name="recovery_attempts",
    )

    op.drop_column(
        "recovery_attempts",
        "scheduled_at",
    )
