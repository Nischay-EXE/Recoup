from app.utils.time import utc_now
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.recovery_models import (
    RecoveryAttempt,
    RecoveryDecisionRecord,
)
from app.state.context import RecoveryContext
from app.state.case_service import get_recovery_case


ACTIVE_ATTEMPT_STATUSES = {
    "proposed",
    "approved",
    "sent",
    "execution_failed",
}


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


def create_recovery_attempt(
    context: RecoveryContext,
    decision: RecoveryDecisionRecord,
    db: Session,
) -> RecoveryAttempt:

    # --------------------------------------------------
    # 1. Prevent duplicate attempt creation
    # --------------------------------------------------
    #
    # If the worker receives the same event again while
    # the existing attempt is still active, return that
    # attempt instead of creating another one.
    #
    # This works together with the idempotent
    # create_recovery_decision() service.
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
    )

    if case is None:
        raise ValueError(
            "Recovery case not found while creating attempt"
        )

    attempt_number = case.current_attempt + 1

    # --------------------------------------------------
    # 3. Create recovery attempt
    # --------------------------------------------------

    attempt = RecoveryAttempt(
        event_id=context.event_id,
        case_id=case.case_id,
        payment_id=context.payment_id,
        order_id=context.order_id,
        customer_id=context.customer_id,

        action=decision.action,
        channel=decision.channel,

        ai_reason=decision.reason,
        ai_confidence=float(decision.confidence),

        # Policy validation is not implemented yet.
        # These fields will be populated by the
        # merchant-policy guard later.
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
    )

    db.add(attempt)
    case.current_attempt = attempt_number
    db.commit()
    db.refresh(attempt)

    return attempt
