from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class RecoveryContext(BaseModel):
    """
    Verified facts available to the recovery system.

    The context is deliberately a data container.
    It does not make recovery decisions.

    Facts should come from:
    - Razorpay webhook data
    - PostgreSQL
    - approved APIs/tools
    """

    # --------------------------------------------------
    # Current event
    # --------------------------------------------------

    event_id: str
    event_type: str
    batch_id: str | None = None

    # --------------------------------------------------
    # Recovery case
    # --------------------------------------------------

    case_id: str | None = None
    current_case_attempt: int = 0

    # --------------------------------------------------
    # Current payment
    # --------------------------------------------------

    payment_id: str | None = None
    order_id: str | None = None

    amount: Decimal | None = None
    currency: str | None = None

    payment_status: str | None = None

    # --------------------------------------------------
    # Customer
    # --------------------------------------------------

    customer_id: str | None = None

    # Derived from stored payment history.
    customer_total_payments: int | None = None
    customer_successful_payments: int | None = None
    customer_failed_payments: int | None = None

    # --------------------------------------------------
    # Payment history
    # --------------------------------------------------

    payment_history: list[dict[str, Any]] = Field(
        default_factory=list
    )

    # --------------------------------------------------
    # Recovery history
    # --------------------------------------------------

    previous_attempts: int = 0

    previous_recovery_attempts: list[dict[str, Any]] = Field(
        default_factory=list
    )

    # --------------------------------------------------
    # Merchant policy
    # --------------------------------------------------

    merchant_policy: dict[str, Any] = Field(
        default_factory=dict
    )

    # --------------------------------------------------
    # Additional verified metadata
    # --------------------------------------------------

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

        # --------------------------------------------------
    # Revenue object
    # --------------------------------------------------

    revenue_object_type: str = "payment"

    payment_id: str | None = None
    order_id: str | None = None
    subscription_id: str | None = None
    invoice_id: str | None = None

    amount: Decimal | None = None
    currency: str | None = None

    # Existing payment compatibility
    payment_status: str | None = None