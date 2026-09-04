from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.recovery_models import (
    RecoveryAttempt,
    RecoveryDecisionRecord,
)
from app.state.context import RecoveryContext
from app.state.case_service import get_recovery_case
from app.utils.time import utc_now


ACTIVE_ATTEMPT_STATUSES = {
    "proposed",
    "approved",
    "sent",
    "execution_failed",
}


# ==========================================================
# RECOVERY CADENCE
# ==========================================================

RECOVERY_CADENCE_MINUTES = {
    1: 0,
    2: 30,
    3: 120,
}


def get_recovery_schedule(
    attempt_number: int,
    *,
    now: datetime | None = None,
) -> datetime:
    """
    Return the deterministic execution time for a recovery attempt.

    Attempt 1:
        immediate

    Attempt 2:
        30 minutes later

    Attempt 3:
        2 hours later
    """

    current_time = now or utc_now()

    delay_minutes = RECOVERY_CADENCE_MINUTES.get(
        attempt_number,
        0,
    )

    return current_time + timedelta(
        minutes=delay_minutes,
    )


# ==========================================================
# ATTEMPT COUNT
# ==========================================================

def get_previous_attempt_count(
    context: RecoveryContext,
    db: Session,
) -> int:
    if context.case_id:
        return (
            db.query(RecoveryAttempt)
            .filter(
                RecoveryAttempt.case_id == context.case_id
            )
            .count()
        )

    return (
        db.query(RecoveryAttempt)
        .filter(
            RecoveryAttempt.event_id == context.event_id
        )
        .count()
    )


# ==========================================================
# CREATE RECOVERY ATTEMPT
# ==========================================================

def create_recovery_attempt(
    context: RecoveryContext,
    decision: RecoveryDecisionRecord,
    db: Session,
) -> RecoveryAttempt:

    # --------------------------------------------------
    # 1. Prevent duplicate attempt creation
    # --------------------------------------------------
    # --------------------------------------------------

    existing_active_attempt = (
        db.query(RecoveryAttempt)
        .filter(
            RecoveryAttempt.event_id == context.event_id,
            RecoveryAttempt.status.in_(
                ACTIVE_ATTEMPT_STATUSES
            ),
        )
        .order_by(
            RecoveryAttempt.attempt_number.desc()
        )
        .first()
    )

    if existing_active_attempt:
        return existing_active_attempt

    # --------------------------------------------------
    # 2. Determine next attempt number
    # --------------------------------------------------

    case = get_recovery_case(
        db,
        case_id=context.case_id,
        order_id=context.order_id,
        payment_id=context.payment_id,
        subscription_id=context.subscription_id,
        invoice_id=context.invoice_id,
    )

    if case is None:
        raise ValueError(
            "Recovery case not found while creating attempt"
        )

    attempt_number = case.current_attempt + 1

    # --------------------------------------------------
    # 3. Determine deterministic execution time
    # --------------------------------------------------

    scheduled_at = get_recovery_schedule(
        attempt_number,
    )

    # --------------------------------------------------
    # 4. Create recovery attempt
    # --------------------------------------------------

    attempt = RecoveryAttempt(
        event_id=context.event_id,
        case_id=case.case_id,
        payment_id=context.payment_id,
        order_id=context.order_id,
        subscription_id=context.subscription_id,
        invoice_id=context.invoice_id,
        customer_id=context.customer_id,
        batch_id=getattr(case, "batch_id", None),

        action=decision.action,
        channel=decision.channel,

        ai_reason=decision.reason,
        ai_confidence=float(decision.confidence),

        policy_result=None,
        policy_reason=None,

        attempt_number=attempt_number,
        status="proposed",

        amount_at_risk=(
            Decimal(str(context.amount))
            if context.amount is not None
            else None
        ),

        amount_recovered=Decimal("0.00"),

        created_at=utc_now(),
        scheduled_at=scheduled_at,
    )

    db.add(attempt)

    case.current_attempt = attempt_number

    db.commit()
    db.refresh(attempt)

    return attempt
