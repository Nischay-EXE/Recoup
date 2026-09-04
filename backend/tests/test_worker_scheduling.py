from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.worker import recovery_worker


def _build_worker_test_objects(
    *,
    scheduled_at,
):
    event_id = "evt_worker_scheduling_test"

    normalized = SimpleNamespace(
        event_id=event_id,
        event_type="payment.failed",
        payment_id="pay_worker_scheduling_test",
        order_id="order_worker_scheduling_test",
        subscription_id=None,
        invoice_id=None,
        customer_id="cust_worker_scheduling_test",
    )

    context = SimpleNamespace(
        case_id="case_worker_scheduling_test",
        current_case_attempt=0,
        amount=Decimal("100.00"),
        payment_status="failed",
        customer_id="cust_worker_scheduling_test",
        order_id="order_worker_scheduling_test",
        payment_id="pay_worker_scheduling_test",
        subscription_id=None,
        invoice_id=None,
        revenue_object_type="payment",
    )

    recovery_case = SimpleNamespace(
        case_id="case_worker_scheduling_test",
        status="open",
        current_attempt=0,
        amount_recovered=Decimal("0.00"),
        amount_at_risk=Decimal("100.00"),
    )

    decision = SimpleNamespace(
        id="decision_worker_scheduling_test",
        action="send_payment_link",
        channel="email",
        confidence=0.95,
        priority="high",
        reason="Recovery payment link.",
    )

    attempt = SimpleNamespace(
        id=123,
        attempt_number=1,
        status="proposed",
        policy_result=None,
        policy_reason=None,
        scheduled_at=scheduled_at,
    )

    normalized_query = MagicMock()
    normalized_query.filter.return_value.first.return_value = normalized

    case_query = MagicMock()
    case_query.filter.return_value.first.return_value = recovery_case

    recovery_attempt_query = MagicMock()
    recovery_attempt_query.filter.return_value.count.return_value = 0
    recovery_attempt_query.filter.return_value.order_by.return_value.first.return_value = None

    db = MagicMock()

    def query_side_effect(model):
        if model is recovery_worker.NormalizedEvent:
            return normalized_query

        if model is recovery_worker.RecoveryCase:
            return case_query

        if model is recovery_worker.RecoveryAttempt:
            return recovery_attempt_query

        return MagicMock()

    db.query.side_effect = query_side_effect

    return (
        event_id,
        normalized,
        context,
        recovery_case,
        decision,
        attempt,
        db,
    )


def test_process_event_does_not_execute_future_scheduled_attempt():
    future_time = recovery_worker.utc_now() + timedelta(
        minutes=30
    )

    (
        event_id,
        normalized,
        context,
        recovery_case,
        decision,
        attempt,
        db,
    ) = _build_worker_test_objects(
        scheduled_at=future_time,
    )

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
            "evaluate_stopping_rules",
            return_value=SimpleNamespace(
                should_stop=False,
                reason="recovery_can_continue",
            ),
        ),
        patch.object(
            recovery_worker,
            "evaluate_escalation_rules",
            return_value=SimpleNamespace(
                should_escalate=False,
                reason="recovery_can_continue",
            ),
        ),
        patch.object(
            recovery_worker,
            "create_recovery_decision",
            return_value=decision,
        ),
        patch.object(
            recovery_worker,
            "validate_recovery_decision",
            return_value=(
                True,
                "Recovery action approved.",
            ),
        ),
        patch.object(
            recovery_worker,
            "get_or_create_recovery_case",
            return_value=recovery_case,
        ),
        patch.object(
            recovery_worker,
            "create_recovery_attempt",
            return_value=attempt,
        ),
        patch.object(
            recovery_worker,
            "execute_recovery_attempt",
        ) as execute_attempt,
    ):
        recovery_worker.process_event(event_id)

    assert attempt.policy_result == "approved"
    assert attempt.status == "approved"

    execute_attempt.assert_not_called()

    db.close.assert_called_once()


def test_process_event_executes_due_scheduled_attempt():
    due_time = recovery_worker.utc_now() - timedelta(
        minutes=1
    )

    (
        event_id,
        normalized,
        context,
        recovery_case,
        decision,
        attempt,
        db,
    ) = _build_worker_test_objects(
        scheduled_at=due_time,
    )

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
            "evaluate_stopping_rules",
            return_value=SimpleNamespace(
                should_stop=False,
                reason="recovery_can_continue",
            ),
        ),
        patch.object(
            recovery_worker,
            "evaluate_escalation_rules",
            return_value=SimpleNamespace(
                should_escalate=False,
                reason="recovery_can_continue",
            ),
        ),
        patch.object(
            recovery_worker,
            "create_recovery_decision",
            return_value=decision,
        ),
        patch.object(
            recovery_worker,
            "validate_recovery_decision",
            return_value=(
                True,
                "Recovery action approved.",
            ),
        ),
        patch.object(
            recovery_worker,
            "get_or_create_recovery_case",
            return_value=recovery_case,
        ),
        patch.object(
            recovery_worker,
            "create_recovery_attempt",
            return_value=attempt,
        ),
        patch.object(
            recovery_worker,
            "execute_recovery_attempt",
            return_value=attempt,
        ) as execute_attempt,
    ):
        recovery_worker.process_event(event_id)

    assert attempt.policy_result == "approved"

    execute_attempt.assert_called_once_with(
        attempt=attempt,
        db=db,
    )

    db.close.assert_called_once()