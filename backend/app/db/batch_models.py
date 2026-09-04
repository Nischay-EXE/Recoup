from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class RecoveryBatch(Base):
    __tablename__ = "recovery_batches"

    id: Mapped[int] = mapped_column(primary_key=True)

    batch_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="active", index=True
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False
    )
