"""generalize recovery cases

Revision ID: 45778f4ac547
Revises: 7133ca3a7956
Create Date: 2026-09-03 22:17:37.492288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45778f4ac547'
down_revision: Union[str, Sequence[str], None] = '7133ca3a7956'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "recovery_cases",
        sa.Column(
            "revenue_object_type",
            sa.String(length=50),
            nullable=True,
        ),
    )

    op.add_column(
        "recovery_cases",
        sa.Column(
            "subscription_id",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "recovery_cases",
        sa.Column(
            "invoice_id",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.create_index(
        op.f("ix_recovery_cases_invoice_id"),
        "recovery_cases",
        ["invoice_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_recovery_cases_revenue_object_type"),
        "recovery_cases",
        ["revenue_object_type"],
        unique=False,
    )

    op.create_index(
        op.f("ix_recovery_cases_subscription_id"),
        "recovery_cases",
        ["subscription_id"],
        unique=False,
    )

    op.execute(
        "UPDATE recovery_cases "
        "SET revenue_object_type = 'payment' "
        "WHERE revenue_object_type IS NULL"
    )

    op.alter_column(
        "recovery_cases",
        "revenue_object_type",
        existing_type=sa.String(length=50),
        nullable=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        op.f("ix_recovery_cases_subscription_id"),
        table_name="recovery_cases",
    )

    op.drop_index(
        op.f("ix_recovery_cases_revenue_object_type"),
        table_name="recovery_cases",
    )

    op.drop_index(
        op.f("ix_recovery_cases_invoice_id"),
        table_name="recovery_cases",
    )

    op.drop_column(
        "recovery_cases",
        "invoice_id",
    )

    op.drop_column(
        "recovery_cases",
        "subscription_id",
    )

    op.drop_column(
        "recovery_cases",
        "revenue_object_type",
    )
