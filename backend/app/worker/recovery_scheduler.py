from __future__ import annotations


from app.db.database import SessionLocal
from app.db.recovery_models import (
    RecoveryAttempt,
    RecoveryCase,
)
from app.state.executor import execute_recovery_attempt
from app.utils.time import utc_now


# ==========================================================
# SCHEDULER CONFIGURATION
# ==========================================================

DEFAULT_BATCH_SIZE = 10

# Terminal states for individual RecoveryAttempt records.
ATTEMPT_TERMINAL_STATUSES = {
    "succeeded",
    "failed",
    "stopped",
    "escalated",
    "blocked",
    "execution_exhausted",
}

# Terminal states for the overall RecoveryCase.
#
# A scheduled attempt must never execute if the case became
# terminal after the attempt was scheduled.
CASE_TERMINAL_STATUSES = {
    "recovered",
    "resolved",
    "closed",
    "escalated",
}


# ==========================================================
# DUE ATTEMPTS
# ==========================================================

def get_due_recovery_attempts(
    db,
    *,
    limit: int = DEFAULT_BATCH_SIZE,
):
    """
    Return recovery attempts that are approved and ready to execute.

    Scheduler responsibility:
        find due work

    Scheduler does NOT:
        - create AI decisions
        - create recovery attempts
        - bypass the guardrail
        - call Razorpay directly
        - execute terminal attempts

    Only persisted, guardrail-approved attempts are eligible.
    """

    now = utc_now()

    return (
        db.query(RecoveryAttempt)
        .filter(
            RecoveryAttempt.status == "approved",
            RecoveryAttempt.policy_result == "approved",
            RecoveryAttempt.scheduled_at.is_not(None),
            RecoveryAttempt.scheduled_at <= now,
        )
        .filter(
            ~RecoveryAttempt.status.in_(
                ATTEMPT_TERMINAL_STATUSES
            )
        )
        .order_by(
            RecoveryAttempt.scheduled_at.asc(),
            RecoveryAttempt.id.asc(),
        )
        .limit(limit)
        .all()
    )


# ==========================================================
# PROCESS DUE ATTEMPTS
# ==========================================================

def process_due_recovery_attempts(
    db,
    *,
    limit: int = DEFAULT_BATCH_SIZE,
) -> int:
    """
    Execute all currently due scheduled recovery attempts.

    Before execution, re-check the recovery case. A case may have
    become terminal after an attempt was scheduled, in which case
    the stale attempt must not be executed.

    Returns:
        Number of attempts successfully handed to the executor.

    Execution failures are isolated to the individual attempt so one
    failing provider call does not prevent other due attempts from being
    processed.
    """

    attempts = get_due_recovery_attempts(
        db,
        limit=limit,
    )

    if not attempts:
        return 0

    processed = 0

    for attempt in attempts:
        try:
            # --------------------------------------------------
            # Re-check the case immediately before execution.
            #
            # The case could have become terminal after this
            # attempt was scheduled.
            # --------------------------------------------------

            recovery_case = (
                db.query(RecoveryCase)
                .filter(
                    RecoveryCase.case_id == attempt.case_id
                )
                .first()
            )

            if (
                recovery_case is not None
                and recovery_case.status in CASE_TERMINAL_STATUSES
            ):
                print(
                    f"[SCHEDULER] Skipping stale recovery attempt "
                    f"attempt_id={attempt.id} "
                    f"case_id={attempt.case_id} "
                    f"case_status={recovery_case.status}"
                )
                continue

            # --------------------------------------------------
            # Case is still active — execute the scheduled
            # recovery attempt through the existing executor.
            # --------------------------------------------------

            print(
                f"[SCHEDULER] Executing due recovery attempt "
                f"attempt_id={attempt.id} "
                f"case_id={attempt.case_id} "
                f"scheduled_at={attempt.scheduled_at} "
                f"action={attempt.action} "
                f"channel={attempt.channel}"
            )

            execute_recovery_attempt(
                attempt=attempt,
                db=db,
            )

            processed += 1

        except Exception as exc:
            print(
                f"[SCHEDULER] Failed to execute scheduled attempt "
                f"attempt_id={attempt.id} "
                f"error={exc}"
            )

    return processed


# ==========================================================
# SINGLE SCHEDULER RUN
# ==========================================================

def run_scheduler_once(
    *,
    limit: int = DEFAULT_BATCH_SIZE,
) -> int:
    """
    Run one scheduler pass.

    A fresh database session is used for each pass so the scheduler
    remains independent from the Redis worker session lifecycle.
    """

    db = SessionLocal()

    try:
        processed = process_due_recovery_attempts(
            db,
            limit=limit,
        )

        print(
            f"[SCHEDULER] Run complete "
            f"processed={processed}"
        )

        return processed

    finally:
        db.close()


# ==========================================================
# SCHEDULER LOOP
# ==========================================================

def run_scheduler() -> None:
    """
    Continuously poll for scheduled recovery attempts.

    This is intentionally a simple polling scheduler for now.

    The cadence can be replaced later with a more sophisticated
    scheduler/queue mechanism without changing the recovery state
    machine or executor.
    """

    import time

    poll_interval_seconds = 30

    print(
        "[SCHEDULER] Recovery scheduler started "
        f"poll_interval={poll_interval_seconds}s"
    )

    while True:
        run_scheduler_once()

        time.sleep(
            poll_interval_seconds
        )


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":
    run_scheduler()