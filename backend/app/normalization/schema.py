from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class NormalizedEvent(BaseModel):
    event_id: str
    source: str
    event_type: str

    # Revenue object identity
    payment_id: str | None = None
    order_id: str | None = None
    subscription_id: str | None = None
    invoice_id: str | None = None

    customer_id: str | None = None

    amount: Decimal | None = None
    amount_paid: Decimal | None = None
    amount_due: Decimal | None = None
    currency: str | None = None

    status: str | None = None

    occurred_at: datetime | None = None
    received_at: datetime | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )
