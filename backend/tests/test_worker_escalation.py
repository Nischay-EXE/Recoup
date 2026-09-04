from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.worker import recovery_worker


def test_process_event_escalates_exhausted_recovery_case():
    event_id = "evt_worker_escalation_test"

    normalized = SimpleNamespace(
        event_id=event_id,
        event_type="payment.failed",
        payment_id="pay_escalation_test",
        order_id="order_escalation_test",
        subscription_id=None,
        invoice_id=None,
        customer_id="cust_escalation_test",
    )

    context = SimpleNamespace(
        case_id="case_escalation_test",
        current_case_attempt=3,
        amount=Decimal("100.00"),
        payment_status="failed",
        customer_id="cust_escalation_test",
        order_id="order_escalation_test",
        payment_id="pay_escalation_test",
        subscription_id=None,
        invoice_id=None,
        revenue_object_type="payment",
    )

    recovery_case = SimpleNamespace(
        case_id="case_escalation_test",
        status="open",
        current_attempt=3,
        amount_recovered=Decimal("0.00"),
        amount_at_risk=Decimal("100.00"),
    )

    escalation_decision = SimpleNamespace(
        should_escalate=True,
        reason="recovery_exhausted",
    )

    decision = SimpleNamespace(
        id="decision_escalation_test",
        action="contact_support",
        channel="none",
        confidence=1.0,
        priority="high",
        reason="Deterministic escalation policy triggered.",
    )

    attempt = SimpleNamespace(
        id=99,
        attempt_number=4,
        status="proposed",
        policy_result=None,
        policy_reason=None,
    )

    normalized_query = MagicMock()
    normalized_query.filter.return_value.first.return_value = normalized

    case_query = MagicMock()
    case_query.filter.return_value.first.return_value = recovery_case

    failed_attempt_query = MagicMock()
    failed_attempt_query.filter.return_value.count.return_value = 3

    db = MagicMock()

    def query_side_effect(model):
        if model is recovery_worker.NormalizedEvent:
            return normalized_query

        if model is recovery_worker.RecoveryCase:
            return case_query

        if model is recovery_worker.RecoveryAttempt:
            return failed_attempt_query

        return MagicMock()

    db.query.side_effect = query_side_effect

    with (
        patch.object(
            recovery_worker,
            "SessionLocal",
            return_value=db,
        ),
        patch.object(
            recovery_worker,
            "process_failed_event",
        ),
        patch.object(
            recovery_worker,
            "build_recovery_context",
            return_value=context,
        ),
        patch.object(
            recovery_worker,
            "evaluate_escalation_rules",
            return_value=escalation_decision,
        ) as evaluate_escalation,
        patch.object(
            recovery_worker,
            "create_recovery_decision",
            return_value=decision,
        ) as create_decision,
        patch.object(
            recovery_worker,
            "validate_recovery_decision",
            return_value=(
                True,
                "Recovery action approved.",
            ),
        ) as validate_decision,
        patch.object(
            recovery_worker,
            "create_recovery_attempt",
            return_value=attempt,
        ) as create_attempt,
       patch.object(
            recovery_worker,
            "create_support_escalation",
            return_value=SimpleNamespace(
                id=123,
                assigned_team="payments",
                priority="high",
            ),
        ) as create_escalation,
        patch.object(
            recovery_worker,
            "execute_recovery_attempt",
            return_value=attempt,
        ) as execute_attempt,
    ):
        recovery_worker.process_event(event_id)

    evaluate_escalation.assert_called_once()

    create_decision.assert_called_once_with(
        context=context,
        db=db,
        action="contact_support",
        channel="none",
        reason=(
            "Deterministic escalation policy triggered: "
            "recovery_exhausted."
        ),
    )

    validate_decision.assert_called_once_with(
        context=context,
        decision=decision,
    )

    create_attempt.assert_called_once_with(
        context=context,
        decision=decision,
        db=db,
    )

    create_escalation.assert_called_once_with(
        db=db,
        case=recovery_case,
        reason_code=escalation_decision.reason,
    )

    execute_attempt.assert_called_once_with(
        attempt=attempt,
        db=db,
    )

    # Escalation must happen before the normal AI recovery path.
    assert decision.action == "contact_support"
    assert decision.channel == "none"

    # The support attempt must be persisted as approved
    # before execution.
    assert attempt.policy_result == "approved"

    db.close.assert_called_once()