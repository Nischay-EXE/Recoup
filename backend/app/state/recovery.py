from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class RecoveryDecision(BaseModel):
    action: Literal[
        "retry_payment",
        "send_payment_link",
        "send_reminder",
        "contact_support",
        "no_action",
    ]

    channel: Literal[
        "whatsapp",
        "email",
        "sms",
        "none",
    ]

    reason: str

    message: str

    confidence: Decimal

    priority: Literal[
        "low",
        "medium",
        "high",
    ]