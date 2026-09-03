from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.normalization.schema import NormalizedEvent


def _unix_timestamp_to_datetime(
    timestamp: Any,
) -> datetime | None:
    """
    Convert a Unix timestamp from Razorpay into a naive UTC datetime.
    """

    if timestamp is None:
        return None

    try:
        return datetime.fromtimestamp(
            int(timestamp),
            tz=timezone.utc,
        ).replace(tzinfo=None)

    except (TypeError, ValueError, OverflowError):
        return None


def normalize_razorpay_event(
    payload: dict[str, Any],
    event_id: str,
    received_at: datetime | None = None,
) -> NormalizedEvent:
    """
    Convert a raw Razorpay webhook payload into our
    canonical NormalizedEvent format.

    The complete raw Razorpay payload is preserved in
    Event.payload.

    This function only extracts the common fields needed
    to correlate and classify the payment event.
    """

    event_type = payload.get(
        "event",
        "unknown",
    )

    payment_entity = (
        payload
        .get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )

    amount_in_smallest_unit = payment_entity.get(
        "amount"
    )

    amount = None

    if amount_in_smallest_unit is not None:
        amount = (
            Decimal(str(amount_in_smallest_unit))
            / Decimal("100")
        )

    normalized_event_type = event_type.replace(
        ".",
        "_",
    )

    # Razorpay event timestamp.
    occurred_at = _unix_timestamp_to_datetime(
        payload.get("created_at")
        or payment_entity.get("created_at")
    )

    return NormalizedEvent(
        event_id=event_id,
        source="razorpay",
        event_type=normalized_event_type,

        customer_id=payment_entity.get(
            "customer_id"
        ),

        payment_id=payment_entity.get(
            "id"
        ),

        order_id=payment_entity.get(
            "order_id"
        ),

        amount=amount,

        currency=payment_entity.get(
            "currency"
        ),

        status=payment_entity.get(
            "status"
        ),

        occurred_at=occurred_at,

        received_at=received_at,
    )