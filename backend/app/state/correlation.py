from sqlalchemy.orm import Session

from app.db.recovery_models import RecoveryAttempt


ACTIVE_RECOVERY_STATUSES = {
    "proposed",
    "approved",
    "sent",
}

CORRELATABLE_RECOVERY_STATUSES = {
    "proposed",
    "approved",
    "sent",
    "succeeded",
    "failed",
    "stopped",
    "escalated",
    "blocked",
    "execution_failed",
    "execution_exhausted",
}


def find_recovery_attempt(
    db: Session,
    *,
    payment_id: str | None = None,
    order_id: str | None = None,
    customer_id: str | None = None,
    recovery_attempt_id: int | str | None = None,
    recovery_case_id: str | None = None,
) -> RecoveryAttempt | None:
    """
    Find the recovery attempt associated with an incoming payment event.

    Correlation priority:
    1. Exact recovery_attempt_id
    2. Exact recovery_case_id when it identifies one attempt
    3. Exact payment_id
    4. Exact order_id
    5. customer_id only when there is exactly one active attempt

    Returns None when the relationship is ambiguous.
    """

    # --------------------------------------------------
    # 1. Exact recovery attempt lineage
    # --------------------------------------------------

    if recovery_attempt_id is not None:
        try:
            attempt_id = int(recovery_attempt_id)
        except (TypeError, ValueError):
            attempt_id = None

        if attempt_id is not None:
            attempt = (
                db.query(RecoveryAttempt)
                .filter(
                    RecoveryAttempt.id == attempt_id,
                    RecoveryAttempt.status.in_(
                        CORRELATABLE_RECOVERY_STATUSES
                    ),
                )
                .first()
            )

            if attempt:
                return attempt

    # --------------------------------------------------
    # 2. Exact recovery case lineage
    # --------------------------------------------------

    if recovery_case_id:
        attempts = (
            db.query(RecoveryAttempt)
            .filter(
                RecoveryAttempt.case_id == recovery_case_id,
                RecoveryAttempt.status.in_(
                    CORRELATABLE_RECOVERY_STATUSES
                ),
            )
            .order_by(
                RecoveryAttempt.attempt_number.desc()
            )
            .all()
        )

        # A recovery case can have multiple attempts.
        # Do not guess which attempt an outcome belongs to.
        #
        # If exactly one attempt is correlatable, use it.
        if len(attempts) == 1:
            return attempts[0]

        # Prefer the currently active attempt if there is
        # exactly one active attempt in the case.
        active_attempts = [
            attempt
            for attempt in attempts
            if attempt.status in ACTIVE_RECOVERY_STATUSES
        ]

        if len(active_attempts) == 1:
            return active_attempts[0]

        # Multiple candidates = ambiguous.
        return None

    # --------------------------------------------------
    # 3. Exact payment match
    # --------------------------------------------------

    if payment_id:
        attempt = (
            db.query(RecoveryAttempt)
            .filter(
                RecoveryAttempt.payment_id == payment_id,
                RecoveryAttempt.status.in_(
                    CORRELATABLE_RECOVERY_STATUSES
                ),
            )
            .order_by(
                RecoveryAttempt.attempt_number.desc()
            )
            .first()
        )

        if attempt:
            return attempt

    # --------------------------------------------------
    # 4. Exact order match
    # --------------------------------------------------

    if order_id:
        attempt = (
            db.query(RecoveryAttempt)
            .filter(
                RecoveryAttempt.order_id == order_id,
                RecoveryAttempt.status.in_(
                    CORRELATABLE_RECOVERY_STATUSES
                ),
            )
            .order_by(
                RecoveryAttempt.attempt_number.desc()
            )
            .first()
        )

        if attempt:
            return attempt

    # --------------------------------------------------
    # 5. Customer fallback
    # --------------------------------------------------

    if customer_id:
        attempts = (
            db.query(RecoveryAttempt)
            .filter(
                RecoveryAttempt.customer_id == customer_id,
                RecoveryAttempt.status.in_(
                    ACTIVE_RECOVERY_STATUSES
                ),
            )
            .order_by(
                RecoveryAttempt.attempt_number.desc()
            )
            .all()
        )

        # Only correlate when there is exactly one
        # active recovery for this customer.
        if len(attempts) == 1:
            return attempts[0]

        # Multiple active recoveries = ambiguous.
        return None

    return None