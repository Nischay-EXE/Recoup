from app.db.database import SessionLocal
from app.state.context_service import build_recovery_context
from app.state.service import create_recovery_decision
from decimal import Decimal
from unittest.mock import MagicMock

from app.state.context import RecoveryContext

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
def make_context():
    return RecoveryContext(
        event_id="evt_service_test",
        event_type="payment_failed",
        payment_id="pay_service_test",
        order_id="order_service_test",
        amount=Decimal("499.00"),
        currency="INR",
        payment_status="failed",
        customer_id="cust_service_test",
        previous_attempts=0,
        previous_recovery_attempts=[],
    )
def test_create_deterministic_escalation_decision():
    context = make_context()

    db = MagicMock()

    query = db.query.return_value
    query.filter.return_value.first.return_value = None

    decision = create_recovery_decision(
        context=context,
        db=db,
        action="contact_support",
        channel="none",
        reason="Deterministic escalation policy triggered.",
    )

    assert decision.action == "contact_support"
    assert decision.channel == "none"
    assert decision.reason == (
        "Deterministic escalation policy triggered."
    )
    assert decision.confidence == 1.0
    assert decision.priority == "high"

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(decision)