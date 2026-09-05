from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class RecoveryContext(BaseModel):
    """Verified facts available to the recovery reasoning pipeline."""

    # Current event / batch
    event_id: str
    event_type: str
    batch_id: str | None = None

    # Recovery case
    case_id: str | None = None
    current_case_attempt: int = 0

    # Revenue object
    revenue_object_type: str = "payment"
    payment_id: str | None = None
    order_id: str | None = None
    subscription_id: str | None = None
    invoice_id: str | None = None

    # Current financial state
    amount: Decimal | None = None
    amount_at_risk: Decimal | None = None
    amount_recovered: Decimal = Decimal("0.00")
    amount_remaining: Decimal | None = None
    currency: str | None = None
    payment_status: str | None = None

    # Customer
    customer_id: str | None = None
    customer_total_payments: int | None = None
    customer_successful_payments: int | None = None
    customer_failed_payments: int | None = None

    # Historical facts
    payment_history: list[dict[str, Any]] = Field(default_factory=list)
    previous_attempts: int = 0
    previous_recovery_attempts: list[dict[str, Any]] = Field(default_factory=list)

    # Merchant policy / verified metadata
    merchant_policy: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
