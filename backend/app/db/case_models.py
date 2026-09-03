from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    case_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    customer_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )

    order_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )

    original_payment_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )

    current_payment_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )

    amount_at_risk: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    amount_recovered: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="open",
        index=True,
    )

    current_attempt: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )