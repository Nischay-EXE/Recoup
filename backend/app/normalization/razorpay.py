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

    The normalizer supports payment, subscription, and
    invoice revenue objects.

    Payment-specific fields are preferred when a payment
    entity is present. Subscription-specific fields are
    used for subscription lifecycle events where a payment
    entity may not exist.
    """

    event_type = payload.get(
        "event",
        "unknown",
    )

    payload_data = payload.get(
        "payload",
        {},
    )

    payment_entity = (
        payload_data
        .get("payment", {})
        .get("entity", {})
    )

    subscription_entity = (
        payload_data
        .get("subscription", {})
        .get("entity", {})
    )

    invoice_entity = (
        payload_data
        .get("invoice", {})
        .get("entity", {})
    )

    # --------------------------------------------------
    # Revenue object IDs
    # --------------------------------------------------

    subscription_id = (
        subscription_entity.get("id")
        or payment_entity.get("subscription_id")
    )

    invoice_id = (
        invoice_entity.get("id")
        or payment_entity.get("invoice_id")
    )

    payment_id = payment_entity.get(
        "id"
    )

    order_id = payment_entity.get(
        "order_id"
    )

    # --------------------------------------------------
    # Customer
    #
    # Payment events normally expose customer_id through
    # payment.entity.
    #
    # Subscription lifecycle events expose customer_id
    # through subscription.entity.
    #
    # Invoice events expose customer_id through
    # invoice.entity.
    # --------------------------------------------------

    customer_id = (
        payment_entity.get("customer_id")
        or subscription_entity.get("customer_id")
        or invoice_entity.get("customer_id")
    )

    # --------------------------------------------------
    # Amount
    #
    # Payment amount is preferred.
    # Invoice amount is used when there is no payment.
    # Subscription lifecycle events may not contain an
    # amount, so amount remains None in that case.
    # --------------------------------------------------

    amount_in_smallest_unit = payment_entity.get(
        "amount"
    )

    if amount_in_smallest_unit is None:
        amount_in_smallest_unit = invoice_entity.get(
            "amount"
        )

    amount = None

    if amount_in_smallest_unit is not None:
        try:
            amount = (
                Decimal(str(amount_in_smallest_unit))
                / Decimal("100")
            )
        except (TypeError, ValueError):
            amount = None

    # --------------------------------------------------
    # Invoice payment amounts
    #
    # Razorpay invoice entities expose amount_paid and
    # amount_due in the smallest currency unit.
    #
    # These remain None for payment/subscription events.
    # --------------------------------------------------

    amount_paid = None
    amount_due = None

    if invoice_entity:
        raw_amount_paid = invoice_entity.get(
            "amount_paid"
        )

        raw_amount_due = invoice_entity.get(
            "amount_due"
        )

        if raw_amount_paid is not None:
            try:
                amount_paid = (
                    Decimal(str(raw_amount_paid))
                    / Decimal("100")
                )
            except (TypeError, ValueError):
                amount_paid = None

        if raw_amount_due is not None:
            try:
                amount_due = (
                    Decimal(str(raw_amount_due))
                    / Decimal("100")
                )
            except (TypeError, ValueError):
                amount_due = None

    # --------------------------------------------------
    # Currency
    # --------------------------------------------------

    currency = (
        payment_entity.get("currency")
        or invoice_entity.get("currency")
    )

    # --------------------------------------------------
    # Status
    #
    # Payment status is preferred when a payment exists.
    # Otherwise use subscription or invoice status.
    # --------------------------------------------------

    status = (
        payment_entity.get("status")
        or subscription_entity.get("status")
        or invoice_entity.get("status")
    )

    normalized_event_type = event_type.replace(
        ".",
        "_",
    )

    # --------------------------------------------------
    # Event timestamp
    # --------------------------------------------------

    occurred_at = _unix_timestamp_to_datetime(
        payload.get("created_at")
        or payment_entity.get("created_at")
        or subscription_entity.get("created_at")
        or invoice_entity.get("created_at")
    )

    return NormalizedEvent(
        event_id=event_id,
        source="razorpay",
        event_type=normalized_event_type,

        customer_id=customer_id,

        payment_id=payment_id,

        order_id=order_id,

        subscription_id=subscription_id,

        invoice_id=invoice_id,

        amount=amount,

        amount_paid=amount_paid,

        amount_due=amount_due,

        currency=currency,

        status=status,

        occurred_at=occurred_at,

        received_at=received_at,
    )