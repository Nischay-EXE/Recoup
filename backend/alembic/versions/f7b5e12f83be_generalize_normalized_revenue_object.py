"""generalize normalized revenue object

Revision ID: f7b5e12f83be
Revises: 8f9b8d2f4c21
Create Date: 2026-09-03 21:43:37.409769

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7b5e12f83be"
down_revision: Union[str, Sequence[str], None] = "8f9b8d2f4c21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "normalized_events",
        sa.Column(
            "subscription_id",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "normalized_events",
        sa.Column(
            "invoice_id",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.create_index(
        op.f("ix_normalized_events_invoice_id"),
        "normalized_events",
        ["invoice_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_normalized_events_subscription_id"),
        "normalized_events",
        ["subscription_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_normalized_events_subscription_id"),
        table_name="normalized_events",
    )

    op.drop_index(
        op.f("ix_normalized_events_invoice_id"),
        table_name="normalized_events",
    )

    op.drop_column(
        "normalized_events",
        "invoice_id",
    )

    op.drop_column(
        "normalized_events",
        "subscription_id",
    )
