from decimal import Decimal

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.models import Event
from app.db.normalized_models import NormalizedEvent
from app.db.recovery_models import RecoveryCase


def _decimal_to_float(
    value: Decimal | None,
) -> float | None:
    if value is None:
        return None

    return float(value)


def _extract_recovery_case_id(
    event: Event,
) -> str | None:
    """
    Extract an explicit recovery case lineage marker from
    a Razorpay payment event.

    Recovery-created payments carry recovery_case_id in
    their payment notes.
    """

    payload = event.payload or {}

    payment_entity = (
        payload
        .get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )

    notes = payment_entity.get("notes") or {}

    if not isinstance(notes, dict):
        return None

    case_id = notes.get("recovery_case_id")

    if not isinstance(case_id, str):
        return None

    case_id = case_id.strip()

    return case_id or None


def _find_recovery_case(
    db: Session,
    *,
    event: Event,
    normalized: NormalizedEvent | None,
) -> tuple[RecoveryCase | None, str]:
    """
    Resolve event → recovery-case lineage without guessing.

    Match priority:

    1. Explicit recovery_case_id from the event payload
    2. Deterministic revenue identifiers:
       - payment_id
       - subscription_id
       - invoice_id
       - order_id

    If exactly one case matches the identifiers, the match is
    considered exact.

    If multiple cases match, the relationship is ambiguous and
    no case is returned.

    Customer ID is intentionally never used as a fallback because
    a customer may have multiple independent recovery cases.
    """

    if normalized is None:
        return None, "none"

    # ---------------------------------------------------------
    # 1. Explicit recovery lineage
    # ---------------------------------------------------------

    explicit_case_id = _extract_recovery_case_id(event)

    if explicit_case_id:
        case = (
            db.query(RecoveryCase)
            .filter(
                RecoveryCase.case_id == explicit_case_id
            )
            .first()
        )

        if case is not None:
            return case, "exact"

    # ---------------------------------------------------------
    # 2. Deterministic identifier matching
    # ---------------------------------------------------------

    identifiers = []

    if normalized.payment_id:
        identifiers.extend(
            [
                RecoveryCase.current_payment_id
                == normalized.payment_id,
                RecoveryCase.original_payment_id
                == normalized.payment_id,
            ]
        )

    if normalized.subscription_id:
        identifiers.append(
            RecoveryCase.subscription_id
            == normalized.subscription_id
        )

    if normalized.invoice_id:
        identifiers.append(
            RecoveryCase.invoice_id
            == normalized.invoice_id
        )

    if normalized.order_id:
        identifiers.append(
            RecoveryCase.order_id
            == normalized.order_id
        )

    if not identifiers:
        return None, "none"

    matching_cases = (
        db.query(RecoveryCase)
        .filter(or_(*identifiers))
        .all()
    )

    # No relationship found.
    if not matching_cases:
        return None, "none"

    # Remove duplicates in case the same case matched more
    # than one identifier.
    unique_cases = {
        case.case_id: case
        for case in matching_cases
    }

    if len(unique_cases) == 1:
        return next(iter(unique_cases.values())), "exact"

    # Multiple possible cases means we must not guess.
    return None, "ambiguous"


def get_recovery_events(
    db: Session,
    *,
    search: str | None = None,
    event_type: str | None = None,
    revenue_object_type: str | None = None,
    batch_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    Read-only event explorer.

    Returns persisted raw event metadata together with normalized
    revenue context and recovery-case lineage where it can be
    determined safely.

    No recovery logic is executed here.
    """

    query = (
        db.query(Event, NormalizedEvent)
        .outerjoin(
            NormalizedEvent,
            NormalizedEvent.event_id
            == Event.event_id,
        )
    )

    if event_type:
        query = query.filter(
            Event.event_type == event_type
        )

    if batch_id:
        query = query.filter(Event.batch_id == batch_id)

    if search:
        pattern = f"%{search}%"

        query = query.filter(
            or_(
                Event.event_id.ilike(pattern),
                Event.event_type.ilike(pattern),
                NormalizedEvent.customer_id.ilike(
                    pattern
                ),
                NormalizedEvent.payment_id.ilike(
                    pattern
                ),
                NormalizedEvent.order_id.ilike(
                    pattern
                ),
                NormalizedEvent.subscription_id.ilike(
                    pattern
                ),
                NormalizedEvent.invoice_id.ilike(
                    pattern
                ),
            )
        )

    if revenue_object_type:
        if revenue_object_type == "payment":
            query = query.filter(
                NormalizedEvent.payment_id.isnot(None)
            )

        elif revenue_object_type == "subscription":
            query = query.filter(
                NormalizedEvent.subscription_id.isnot(None)
            )

        elif revenue_object_type == "invoice":
            query = query.filter(
                NormalizedEvent.invoice_id.isnot(None)
            )

    total = (
        query
        .with_entities(func.count(Event.id))
        .scalar()
        or 0
    )

    rows = (
        query
        .order_by(
            Event.received_at.desc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []

    for event, normalized in rows:
        recovery_case, recovery_case_match = (
            _find_recovery_case(
                db,
                event=event,
                normalized=normalized,
            )
        )

        items.append(
            {
                "event_id": event.event_id,
                "batch_id": event.batch_id,
                "source": event.source,
                "event_type": event.event_type,
                "received_at": event.received_at,
                "payload_available": (
                    event.payload is not None
                ),

                "normalized": (
                    {
                        "event_id": normalized.event_id,
                        "customer_id": normalized.customer_id,
                        "payment_id": normalized.payment_id,
                        "order_id": normalized.order_id,
                        "subscription_id": (
                            normalized.subscription_id
                        ),
                        "invoice_id": normalized.invoice_id,
                        "amount": _decimal_to_float(
                            normalized.amount
                        ),
                        "amount_paid": _decimal_to_float(
                            normalized.amount_paid
                        ),
                        "amount_due": _decimal_to_float(
                            normalized.amount_due
                        ),
                        "currency": normalized.currency,
                        "status": normalized.status,
                        "occurred_at": (
                            normalized.occurred_at
                        ),
                        "received_at": (
                            normalized.received_at
                        ),
                    }
                    if normalized
                    else None
                ),

                "recovery_case": (
                    {
                        "case_id": recovery_case.case_id,
                        "status": recovery_case.status,
                        "revenue_object_type": (
                            recovery_case.revenue_object_type
                        ),
                        "amount_at_risk": (
                            _decimal_to_float(
                                recovery_case.amount_at_risk
                            )
                        ),
                        "amount_recovered": (
                            _decimal_to_float(
                                recovery_case.amount_recovered
                            )
                        ),
                        "current_attempt": (
                            recovery_case.current_attempt
                        ),
                    }
                    if recovery_case
                    else None
                ),

                "recovery_case_match": (
                    recovery_case_match
                ),
            }
        )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }