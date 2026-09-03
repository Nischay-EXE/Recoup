from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class RecoveryDecisionRecord(Base):
    __tablename__ = "recovery_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    channel: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Numeric(4, 3),
        nullable=False,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class RecoveryAttempt(Base):
    __tablename__ = "recovery_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)

    event_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    case_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    payment_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    order_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    customer_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    channel: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    ai_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    ai_confidence: Mapped[float | None] = mapped_column(
        Numeric(4, 3),
        nullable=True,
    )

    policy_result: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    policy_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    attempt_number: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="proposed",
        index=True,
    )

    amount_at_risk: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    amount_recovered: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        default=Decimal("0.00"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    # --------------------------------------------------
    # Executor metadata
    # --------------------------------------------------

    execution_provider: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    external_execution_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    external_execution_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    execution_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"

    id: Mapped[int] = mapped_column(primary_key=True)

    case_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    customer_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    order_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    original_payment_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    current_payment_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
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
