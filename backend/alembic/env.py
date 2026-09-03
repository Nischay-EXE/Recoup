from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from app.config import settings
from app.db.database import Base, engine

# Import all model modules so SQLAlchemy knows about every table.
from app.db import models  # noqa: F401
from app.db import normalized_models  # noqa: F401
from app.db import history_models  # noqa: F401
from app.db import recovery_models  # noqa: F401
from app.db import decision_models  # noqa: F401


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic compares the database against this metadata.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""

    url = settings.database_url

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()