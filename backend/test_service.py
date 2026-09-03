from app.db.database import SessionLocal
from app.state.context_service import build_recovery_context
from app.state.service import create_recovery_decision


TEST_EVENT_ID = "evt_test_007"

db = SessionLocal()

try:
    context = build_recovery_context(TEST_EVENT_ID, db)

    print("\n===== RECOVERY CONTEXT =====")
    print(context.model_dump())

    decision = create_recovery_decision(
        context=context,
        db=db,
    )

    print("\n===== FINAL DECISION =====")
    print({
        "id": decision.id,
        "event_id": decision.event_id,
        "action": decision.action,
        "channel": decision.channel,
        "reason": decision.reason,
        "message": decision.message,
        "confidence": decision.confidence,
        "priority": decision.priority,
    })

finally:
    db.close()