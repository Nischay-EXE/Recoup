from app.utils.time import utc_now
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.normalized_models import NormalizedEvent
from app.db.recovery_models import (
    RecoveryAttempt,
    RecoveryCase,
)
from app.state.case_service import (
    get_recovery_case,
    mark_case_recovered,
)


FINAL_STATUSES = {
    "succeeded",
    "failed",
    "stopped",
    "escalated",
    "blocked",
    "execution_exhausted",
}


def mark_recovery_succeeded(
    attempt: RecoveryAttempt,
    db: Session,
    amount_recovered: Decimal | None = None,
) -> RecoveryAttempt:
    """
    Mark a sent recovery attempt as successfully recovered.
    """

    if attempt.status in FINAL_STATUSES:
        return attempt

    if attempt.status != "sent":
        raise ValueError(
            f"Cannot mark attempt as succeeded from status "
            f"'{attempt.status}'. Expected 'sent'."
        )

    recovered_amount = (
        amount_recovered
        if amount_recovered is not None
        else attempt.amount_at_risk
    )

    attempt.status = "succeeded"
    attempt.amount_recovered = recovered_amount
    attempt.resolved_at = utc_now()

    case = get_recovery_case(
        db,
        case_id=attempt.case_id,
        order_id=attempt.order_id,
        payment_id=attempt.payment_id,
        subscription_id=attempt.subscription_id,
        invoice_id=attempt.invoice_id,
    )

    db.commit()
    db.refresh(attempt)

    if case is not None:
        mark_case_recovered(
            db,
            case,
            payment_id=attempt.payment_id,
            amount_recovered=recovered_amount or Decimal("0.00"),
        )

    return attempt


def record_invoice_partial_payment(
    normalized: NormalizedEvent,
    db: Session,
) -> RecoveryCase | None:
    """
    Record a partial payment against an invoice recovery case.

    Razorpay's invoice.amount_paid is cumulative, so only the
    delta between the current amount_paid and the case's
    previously recorded amount_recovered is counted.

    A partial payment does not close the recovery case while
    amount_due remains greater than zero.

    Repeated delivery of the same invoice.partially_paid event
    is therefore idempotent.
    """

    if not normalized.invoice_id:
        print(
            f"[WORKER] Partial invoice payment has no invoice_id "
            f"event={normalized.event_id}"
        )
        return None

    case = get_recovery_case(
        db,
        invoice_id=normalized.invoice_id,
    )

    if case is None:
        print(
            f"[WORKER] Partial invoice payment has no "
            f"matching recovery case "
            f"event={normalized.event_id} "
            f"invoice_id={normalized.invoice_id}"
        )
        return None

    cumulative_amount_paid = (
        normalized.amount_paid
        if normalized.amount_paid is not None
        else Decimal("0.00")
    )

    previously_recovered = (
        case.amount_recovered
        or Decimal("0.00")
    )

    newly_recovered = (
        cumulative_amount_paid
        - previously_recovered
    )

    # --------------------------------------------------
    # Duplicate / stale webhook protection
    # --------------------------------------------------

    if newly_recovered <= Decimal("0.00"):
        print(
            f"[WORKER] Invoice partial payment already accounted for "
            f"event={normalized.event_id} "
            f"invoice_id={normalized.invoice_id} "
            f"amount_paid={cumulative_amount_paid} "
            f"case_amount_recovered={previously_recovered}"
        )
        return case

    # --------------------------------------------------
    # Record only the newly recovered amount
    # --------------------------------------------------

    case.amount_recovered = (
        previously_recovered
        + newly_recovered
    )

    # --------------------------------------------------
    # A partial payment keeps the case open.
    #
    # The invoice.paid event is responsible for the final
    # recovery transition.
    # --------------------------------------------------

    if (
        normalized.amount_due is not None
        and normalized.amount_due <= Decimal("0.00")
    ):
        case.status = "recovered"
        case.resolved_at = utc_now()

    db.commit()
    db.refresh(case)

    print(
        f"[WORKER] Invoice partial payment recorded "
        f"event={normalized.event_id} "
        f"invoice_id={normalized.invoice_id} "
        f"newly_recovered={newly_recovered} "
        f"total_recovered={case.amount_recovered} "
        f"amount_due={normalized.amount_due} "
        f"case_status={case.status}"
    )

    return case


def mark_recovery_failed(
    attempt: RecoveryAttempt,
    db: Session,
) -> RecoveryAttempt:
    """
    Mark a sent recovery attempt as failed.
    """

    if attempt.status in FINAL_STATUSES:
        return attempt

    if attempt.status != "sent":
        raise ValueError(
            f"Cannot mark attempt as failed from status "
            f"'{attempt.status}'. Expected 'sent'."
        )

    attempt.status = "failed"
    attempt.amount_recovered = Decimal("0.00")
    attempt.resolved_at = utc_now()

    db.commit()
    db.refresh(attempt)

    return attempt