from app.db.database import SessionLocal
from app.db.recovery_models import RecoveryAttempt
from app.state.executor import execute_recovery_attempt


TEST_EVENT_ID = "evt_test_007"

db = SessionLocal()

try:
    attempt = (
        db.query(RecoveryAttempt)
        .filter(
            RecoveryAttempt.event_id == TEST_EVENT_ID
        )
        .order_by(
            RecoveryAttempt.attempt_number.desc()
        )
        .first()
    )

    if attempt is None:
        raise RuntimeError(
            f"No recovery attempt found for {TEST_EVENT_ID}"
        )

    print("\n===== BEFORE EXECUTION =====")
    print({
        "id": attempt.id,
        "event_id": attempt.event_id,
        "action": attempt.action,
        "channel": attempt.channel,
        "attempt_number": attempt.attempt_number,
        "status": attempt.status,
        "amount_at_risk": str(attempt.amount_at_risk),
        "amount_recovered": str(attempt.amount_recovered),
        "executed_at": attempt.executed_at,
        "resolved_at": attempt.resolved_at,
    })

    result = execute_recovery_attempt(
        attempt=attempt,
        db=db,
    )

    print("\n===== AFTER EXECUTION =====")
    print({
        "id": result.id,
        "event_id": result.event_id,
        "action": result.action,
        "channel": result.channel,
        "attempt_number": result.attempt_number,
        "status": result.status,
        "amount_at_risk": str(result.amount_at_risk),
        "amount_recovered": str(result.amount_recovered),
        "executed_at": result.executed_at,
        "resolved_at": result.resolved_at,
    })

finally:
    db.close()