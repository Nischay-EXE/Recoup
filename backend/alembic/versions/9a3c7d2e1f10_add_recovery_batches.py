"""add recovery batches

Revision ID: 9a3c7d2e1f10
Revises: 5678290fd7e6
"""
from alembic import op
import sqlalchemy as sa

revision = "9a3c7d2e1f10"
down_revision = "5678290fd7e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recovery_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_recovery_batches_batch_id", "recovery_batches", ["batch_id"], unique=True)
    op.create_index("ix_recovery_batches_status", "recovery_batches", ["status"], unique=False)

    for table in ["events", "normalized_events", "recovery_cases", "recovery_attempts", "recovery_decisions", "recovery_escalations"]:
        op.add_column(table, sa.Column("batch_id", sa.String(length=255), nullable=True))
        op.create_index(f"ix_{table}_batch_id", table, ["batch_id"], unique=False)


def downgrade() -> None:
    for table in ["recovery_escalations", "recovery_decisions", "recovery_attempts", "recovery_cases", "normalized_events", "events"]:
        op.drop_index(f"ix_{table}_batch_id", table_name=table)
        op.drop_column(table, "batch_id")
    op.drop_index("ix_recovery_batches_status", table_name="recovery_batches")
    op.drop_index("ix_recovery_batches_batch_id", table_name="recovery_batches")
    op.drop_table("recovery_batches")
