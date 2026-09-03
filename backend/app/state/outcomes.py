from app.utils.time import utc_now
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.recovery_models import RecoveryAttempt
from app.state.case_service import get_recovery_case, mark_case_recovered


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
    )

    db.commit()
    db.refresh(attempt)

    if case is not None:
        mark_case_recovered(
            db,
            case,
            payment_id=attempt.payment_id or "",
            amount_recovered=recovered_amount or Decimal("0.00"),
        )

    return attempt


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
