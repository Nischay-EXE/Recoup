"""link recovery attempts to cases

Revision ID: 0735cc4ab24e
Revises: 3d73201606e5
Create Date: 2026-09-01 13:50:05.258756

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0735cc4ab24e'
down_revision: Union[str, Sequence[str], None] = '3d73201606e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "recovery_attempts",
        sa.Column(
            "case_id",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_recovery_attempts_case_id",
        "recovery_attempts",
        ["case_id"],
    )

    op.create_foreign_key(
        "fk_recovery_attempts_case_id",
        "recovery_attempts",
        "recovery_cases",
        ["case_id"],
        ["case_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_recovery_attempts_case_id",
        "recovery_attempts",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_recovery_attempts_case_id",
        table_name="recovery_attempts",
    )

    op.drop_column(
        "recovery_attempts",
        "case_id",
    )
