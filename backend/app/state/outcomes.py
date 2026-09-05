from app.utils.time import utc_now
from datetime import datetime

from app.db.models import Event
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.normalized_models import NormalizedEvent
from app.db.recovery_models import (
    RecoveryAttempt,
    RecoveryCase,
)
from app.state.case_service import (
    get_recovery_case,
    get_recovery_case_by_invoice,
    create_recovery_case,
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
    """Record a cumulative invoice partial payment and keep the case open.

    Razorpay invoice webhooks can contain a nested payment entity whose
    ``amount`` is only the amount of the payment being made.  For invoice
    recovery, the authoritative financial fields are on ``invoice.entity``:
    total ``amount``, cumulative ``amount_paid`` and ``amount_due``.

    The raw Event payload is preferred when available so the accounting state
    cannot be corrupted by a lossy/incorrect normalization step.  The case is
    recovered only when cumulative paid >= invoice total (or due <= 0).
    """
    if not normalized.invoice_id:
        print(
            f"[WORKER] Partial invoice payment has no invoice_id "
            f"event={normalized.event_id}"
        )
        return None

    invoice_total = normalized.amount
    cumulative_amount_paid = normalized.amount_paid
    raw_amount_due = normalized.amount_due
    raw_invoice_status = normalized.status

    # Re-read the exact raw webhook. This is the strongest source for invoice
    # accounting because it contains the invoice entity separately from the
    # nested payment entity.
    source_event = (
        db.query(Event)
        .filter(Event.event_id == normalized.event_id)
        .first()
    )

    if source_event and isinstance(source_event.payload, dict):
        invoice_entity = (
            source_event.payload
            .get("payload", {})
            .get("invoice", {})
            .get("entity", {})
        )
        if isinstance(invoice_entity, dict) and invoice_entity:
            raw_total = invoice_entity.get("amount")
            raw_paid = invoice_entity.get("amount_paid")
            raw_due = invoice_entity.get("amount_due")
            raw_status = invoice_entity.get("status")

            def money(value):
                if value is None:
                    return None
                try:
                    return Decimal(str(value)) / Decimal("100")
                except (TypeError, ValueError, ArithmeticError):
                    return None

            parsed_total = money(raw_total)
            parsed_paid = money(raw_paid)
            parsed_due = money(raw_due)

            if parsed_total is not None:
                invoice_total = parsed_total
            if parsed_paid is not None:
                cumulative_amount_paid = parsed_paid
            if parsed_due is not None:
                raw_amount_due = parsed_due
            if raw_status:
                raw_invoice_status = str(raw_status)

    if invoice_total is None:
        if cumulative_amount_paid is not None and raw_amount_due is not None:
            invoice_total = cumulative_amount_paid + raw_amount_due
        else:
            print(
                f"[WORKER] Partial invoice payment missing invoice total "
                f"event={normalized.event_id} invoice_id={normalized.invoice_id}"
            )
            return None

    invoice_total = max(invoice_total, Decimal("0.00"))
    cumulative_amount_paid = max(
        cumulative_amount_paid or Decimal("0.00"),
        Decimal("0.00"),
    )
    cumulative_amount_paid = min(cumulative_amount_paid, invoice_total)

    calculated_amount_due = max(
        invoice_total - cumulative_amount_paid,
        Decimal("0.00"),
    )

    # If Razorpay supplied a non-zero due, retain it only as diagnostic data;
    # the case balance is always derived from total - cumulative paid.
    supplied_amount_due = raw_amount_due

    case = get_recovery_case_by_invoice(
        db,
        invoice_id=normalized.invoice_id,
    )

    if case is None:
        case = create_recovery_case(
            db,
            customer_id=normalized.customer_id,
            order_id=normalized.order_id,
            payment_id=normalized.payment_id,
            amount=invoice_total,
            revenue_object_type="invoice",
            subscription_id=normalized.subscription_id,
            invoice_id=normalized.invoice_id,
            batch_id=normalized.batch_id,
        )
    else:
        # Never allow an earlier incorrect terminal state to hide an unpaid
        # invoice.  A partial payment with money outstanding is recoverable.
        if case.status in {"recovered", "resolved", "closed"} and calculated_amount_due > 0:
            case.status = "open"
            case.resolved_at = None

        # The invoice total is authoritative for invoice cases. Do not replace
        # it with a nested payment amount.
        case.amount_at_risk = invoice_total

    previously_recovered = case.amount_recovered or Decimal("0.00")

    # Razorpay's amount_paid is cumulative. Never decrease the recorded
    # recovery because an older/duplicate webhook arrived out of order.
    if cumulative_amount_paid > previously_recovered:
        case.amount_recovered = cumulative_amount_paid

    if normalized.payment_id:
        case.current_payment_id = normalized.payment_id

    if calculated_amount_due <= Decimal("0.00"):
        case.amount_recovered = invoice_total
        case.status = "recovered"
        case.resolved_at = utc_now()
    else:
        case.status = "open"
        case.resolved_at = None

    db.commit()
    db.refresh(case)

    print(
        f"[WORKER] Invoice partial payment recorded "
        f"event={normalized.event_id} "
        f"invoice_id={normalized.invoice_id} "
        f"invoice_total={invoice_total} "
        f"amount_paid={cumulative_amount_paid} "
        f"amount_due={calculated_amount_due} "
        f"supplied_amount_due={supplied_amount_due} "
        f"previous_recovered={previously_recovered} "
        f"total_recovered={case.amount_recovered} "
        f"case_status={case.status} "
        f"invoice_status={raw_invoice_status}"
    )

    return case

def mark_invoice_recovered_without_attempt(
    normalized: NormalizedEvent,
    db: Session,
) -> RecoveryCase | None:
    """
    Finalize an invoice case on invoice.paid even when no `sent` recovery
    attempt can be correlated (for example, payment before a scheduled
    reminder executes).
    """

    if not normalized.invoice_id:
        return None

    case = get_recovery_case_by_invoice(
        db,
        invoice_id=normalized.invoice_id,
    )
    if case is None:
        return None

    total_recovered = (
        normalized.amount
        if normalized.amount is not None
        else (
            normalized.amount_paid
            if normalized.amount_paid is not None
            else case.amount_at_risk
        )
    ) or Decimal("0.00")

    case.amount_recovered = min(
        total_recovered,
        case.amount_at_risk or total_recovered,
    )
    case.status = "recovered"
    case.resolved_at = utc_now()

    pending_attempts = (
        db.query(RecoveryAttempt)
        .filter(
            RecoveryAttempt.case_id == case.case_id,
            RecoveryAttempt.status.in_(
                {"proposed", "approved", "execution_failed"}
            ),
        )
        .all()
    )

    for pending_attempt in pending_attempts:
        pending_attempt.status = "stopped"
        pending_attempt.resolved_at = utc_now()
        pending_attempt.execution_error = (
            "Invoice was fully paid before the scheduled recovery attempt executed."
        )

    db.commit()
    db.refresh(case)

    print(
        f"[WORKER] Invoice recovery finalized "
        f"event={normalized.event_id} "
        f"invoice_id={normalized.invoice_id} "
        f"case_id={case.case_id} "
        f"amount_recovered={case.amount_recovered} "
        f"stopped_scheduled_attempts={len(pending_attempts)}"
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
