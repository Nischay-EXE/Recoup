from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class NormalizedEvent(Base):
    __tablename__ = "normalized_events"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    event_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )

    customer_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    payment_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )

    order_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )

    subscription_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )

    invoice_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )

    amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    amount_paid: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    amount_due: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    currency: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    batch_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )

    received_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )


