from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.state.audit import get_recovery_case_timeline


def test_get_recovery_case_timeline_returns_chronological_history():
    db = MagicMock()

    case_created_at = datetime(2026, 9, 4, 10, 0, 0)
    decision_at = datetime(2026, 9, 4, 10, 1, 0)
    attempt_created_at = datetime(2026, 9, 4, 10, 2, 0)
    scheduled_at = datetime(2026, 9, 4, 10, 30, 0)
    executed_at = datetime(2026, 9, 4, 10, 31, 0)
    resolved_at = datetime(2026, 9, 4, 10, 32, 0)

    case = SimpleNamespace(
        case_id="case_001",
        customer_id="cust_001",
        revenue_object_type="payment",
        amount_at_risk=Decimal("1000.00"),
        amount_recovered=Decimal("1000.00"),
        status="recovered",
        created_at=case_created_at,
        resolved_at=resolved_at,
    )

    attempt = SimpleNamespace(
        id=101,
        case_id="case_001",
        event_id="evt_001",
        attempt_number=1,
        action="send_payment_link",
        channel="email",
        status="succeeded",
        amount_recovered=Decimal("1000.00"),
        execution_provider="razorpay",
        external_execution_id="plink_001",
        external_execution_url="https://example.com/payment/plink_001",
        execution_error=None,
        policy_result="allowed",
        policy_reason="Payment recovery action is permitted.",
        created_at=attempt_created_at,
        scheduled_at=scheduled_at,
        executed_at=executed_at,
        resolved_at=resolved_at,
    )

    decision = SimpleNamespace(
        id=201,
        event_id="evt_001",
        action="send_payment_link",
        channel="email",
        reason="Payment failed and recovery is viable",
        message="Please complete your payment using the provided link.",
        confidence=0.95,
        priority="high",
        created_at=decision_at,
    )

        # First query -> case
    case_query = MagicMock()
    case_query.filter.return_value.first.return_value = case

    # Second query -> attempts
    attempt_query = MagicMock()
    attempt_query.filter.return_value.order_by.return_value.all.return_value = [
        attempt
    ]

    # Third query -> decisions
    decision_query = MagicMock()
    decision_query.filter.return_value.all.return_value = [
        decision
    ]

    # Fourth query -> escalation
    escalation_query = MagicMock()
    escalation_query.filter.return_value.first.return_value = None

    db.query.side_effect = [
        case_query,
        attempt_query,
        decision_query,
        escalation_query,
    ]

    result = get_recovery_case_timeline(
        "case_001",
        db,
    )

    assert result["case_id"] == "case_001"
    assert result["status"] == "recovered"
    assert result["amount_at_risk"] == Decimal("1000.00")
    assert result["amount_recovered"] == Decimal("1000.00")

    timeline = result["timeline"]

    assert [
        item["event_type"]
        for item in timeline
    ] == [
        "case_created",
        "decision_created",
        "guardrail_evaluated",
        "attempt_created",
        "attempt_scheduled",
        "attempt_executed",
        "attempt_resolved",
        "case_resolved",
    ]

    assert timeline[1]["details"]["action"] == "send_payment_link"
    assert timeline[1]["details"]["channel"] == "email"

    assert timeline[2]["details"]["attempt_number"] == 1

    assert timeline[5]["details"]["external_execution_id"] == "plink_001"

    assert timeline[6]["details"]["amount_recovered"] == Decimal(
        "1000.00"
    )


def test_get_recovery_case_timeline_raises_for_missing_case():
    db = MagicMock()

    case_query = MagicMock()
    case_query.filter.return_value.first.return_value = None

    db.query.return_value = case_query

    try:
        get_recovery_case_timeline(
            "missing_case",
            db,
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert str(exc) == (
            "Recovery case not found: missing_case"
        )