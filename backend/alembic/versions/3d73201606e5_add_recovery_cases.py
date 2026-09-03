"""add recovery cases

Revision ID: 3d73201606e5
Revises: d1d64e11421b
Create Date: 2026-09-01 13:05:31.499113
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3d73201606e5"
down_revision: Union[str, Sequence[str], None] = "d1d64e11421b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recovery_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "case_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "order_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "original_payment_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "current_payment_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "amount_at_risk",
            sa.Numeric(12, 2),
            nullable=True,
        ),
        sa.Column(
            "amount_recovered",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "current_attempt",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "resolved_at",
            sa.DateTime(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_recovery_cases_case_id",
        "recovery_cases",
        ["case_id"],
        unique=True,
    )

    op.create_index(
        "ix_recovery_cases_customer_id",
        "recovery_cases",
        ["customer_id"],
    )

    op.create_index(
        "ix_recovery_cases_order_id",
        "recovery_cases",
        ["order_id"],
    )

    op.create_index(
        "ix_recovery_cases_original_payment_id",
        "recovery_cases",
        ["original_payment_id"],
    )

    op.create_index(
        "ix_recovery_cases_current_payment_id",
        "recovery_cases",
        ["current_payment_id"],
    )

    op.create_index(
        "ix_recovery_cases_status",
        "recovery_cases",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_recovery_cases_status",
        table_name="recovery_cases",
    )
    op.drop_index(
        "ix_recovery_cases_current_payment_id",
        table_name="recovery_cases",
    )
    op.drop_index(
        "ix_recovery_cases_original_payment_id",
        table_name="recovery_cases",
    )
    op.drop_index(
        "ix_recovery_cases_order_id",
        table_name="recovery_cases",
    )
    op.drop_index(
        "ix_recovery_cases_customer_id",
        table_name="recovery_cases",
    )
    op.drop_index(
        "ix_recovery_cases_case_id",
        table_name="recovery_cases",
    )
    op.drop_table("recovery_cases")