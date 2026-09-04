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


BATCH_TABLES = [
    "events",
    "normalized_events",
    "recovery_cases",
    "recovery_attempts",
    "recovery_decisions",
    "recovery_escalations",
]


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return any(
        column["name"] == column_name
        for column in inspector.get_columns(table_name)
    )


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    return any(
        index["name"] == index_name
        for index in inspector.get_indexes(table_name)
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # The FastAPI application historically calls Base.metadata.create_all().
    # That can create newly-added tables before Alembic reaches their
    # migration. Make this migration safe for that existing schema while
    # still allowing Alembic to own the missing columns/indexes.
    if not _table_exists(inspector, "recovery_batches"):
        op.create_table(
            "recovery_batches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("batch_id", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "status",
                sa.String(length=30),
                nullable=False,
                server_default="active",
            ),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

        inspector = sa.inspect(bind)

    if not _index_exists(
        inspector,
        "recovery_batches",
        "ix_recovery_batches_batch_id",
    ):
        op.create_index(
            "ix_recovery_batches_batch_id",
            "recovery_batches",
            ["batch_id"],
            unique=True,
        )

    inspector = sa.inspect(bind)
    if not _index_exists(
        inspector,
        "recovery_batches",
        "ix_recovery_batches_status",
    ):
        op.create_index(
            "ix_recovery_batches_status",
            "recovery_batches",
            ["status"],
            unique=False,
        )

    for table in BATCH_TABLES:
        inspector = sa.inspect(bind)

        if not _table_exists(inspector, table):
            continue

        if not _column_exists(inspector, table, "batch_id"):
            op.add_column(
                table,
                sa.Column(
                    "batch_id",
                    sa.String(length=255),
                    nullable=True,
                ),
            )

        inspector = sa.inspect(bind)
        index_name = f"ix_{table}_batch_id"

        if not _index_exists(inspector, table, index_name):
            op.create_index(
                index_name,
                table,
                ["batch_id"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table in reversed(BATCH_TABLES):
        inspector = sa.inspect(bind)

        if not _table_exists(inspector, table):
            continue

        index_name = f"ix_{table}_batch_id"
        if _index_exists(inspector, table, index_name):
            op.drop_index(index_name, table_name=table)

        inspector = sa.inspect(bind)
        if _column_exists(inspector, table, "batch_id"):
            op.drop_column(table, "batch_id")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "recovery_batches"):
        if _index_exists(
            inspector,
            "recovery_batches",
            "ix_recovery_batches_status",
        ):
            op.drop_index(
                "ix_recovery_batches_status",
                table_name="recovery_batches",
            )

        inspector = sa.inspect(bind)
        if _index_exists(
            inspector,
            "recovery_batches",
            "ix_recovery_batches_batch_id",
        ):
            op.drop_index(
                "ix_recovery_batches_batch_id",
                table_name="recovery_batches",
            )

        op.drop_table("recovery_batches")
