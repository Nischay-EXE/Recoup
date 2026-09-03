"""add execution metadata to recovery attempts

Revision ID: 8f9b8d2f4c21
Revises: 0735cc4ab24e
Create Date: 2026-09-02 23:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f9b8d2f4c21"
down_revision: Union[str, Sequence[str], None] = "0735cc4ab24e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "recovery_attempts",
        sa.Column(
            "execution_provider",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.add_column(
        "recovery_attempts",
        sa.Column(
            "external_execution_id",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "recovery_attempts",
        sa.Column(
            "external_execution_url",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "recovery_attempts",
        sa.Column(
            "execution_error",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "recovery_attempts",
        "execution_error",
    )
    op.drop_column(
        "recovery_attempts",
        "external_execution_url",
    )
    op.drop_column(
        "recovery_attempts",
        "external_execution_id",
    )
    op.drop_column(
        "recovery_attempts",
        "execution_provider",
    )
