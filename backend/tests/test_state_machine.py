from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.state.executor import execute_recovery_attempt


@pytest.mark.parametrize(
    "status",
    [
        "succeeded",
        "failed",
        "stopped",
        "escalated",
        "blocked",
        "execution_exhausted",
        "sent",
    ],
)
def test_terminal_or_already_executed_attempt_is_not_executed_again(status):
    attempt = MagicMock()
    attempt.id = 999
    attempt.event_id = "evt_state_machine_test"
    attempt.action = "send_payment_link"
    attempt.channel = "email"
    attempt.status = status

    db = MagicMock()

    with patch("app.state.executor.execute_strategy") as execute_strategy:
        result = execute_recovery_attempt(
            attempt=attempt,
            db=db,
        )

    assert result is attempt
    assert attempt.status == status
    execute_strategy.assert_not_called()


def test_execution_failed_attempt_is_retryable():
    attempt = MagicMock()
    attempt.id = 1000
    attempt.event_id = "evt_retry_state_machine_test"
    attempt.action = "send_payment_link"
    attempt.channel = "email"
    attempt.status = "execution_failed"
    attempt.resolved_at = None

    decision = MagicMock()
    decision.action = "send_payment_link"
    decision.channel = "email"

    db = MagicMock()

    decision_query = MagicMock()
    decision_query.filter.return_value.first.return_value = decision
    db.query.return_value = decision_query

    with (
        patch(
            "app.state.executor.build_recovery_context",
            return_value=MagicMock(),
        ),
        patch(
            "app.state.executor.execute_strategy",
            side_effect=RuntimeError("temporary failure"),
        ) as execute_strategy,
    ):
        with pytest.raises(RuntimeError, match="temporary failure"):
            execute_recovery_attempt(
                attempt=attempt,
                db=db,
            )

    assert attempt.status == "execution_failed"
    assert attempt.resolved_at is None
    execute_strategy.assert_called_once()


def test_new_attempt_increments_case_attempt_number_after_terminal_attempt():
    from app.state.attempts import create_recovery_attempt
    from app.db.recovery_models import RecoveryAttempt, RecoveryCase

    case = SimpleNamespace(
        case_id="case_state_machine_progression",
        current_attempt=1,
    )

    context = SimpleNamespace(
        event_id="evt_state_machine_next",
        case_id=case.case_id,
        order_id="order_state_machine",
        payment_id="pay_state_machine",
        subscription_id=None,
        invoice_id=None,
        customer_id="cust_state_machine",
        amount=Decimal("500.00"),
    )

    decision = SimpleNamespace(
        action="send_payment_link",
        channel="email",
        reason="retry",
        confidence=0.9,
    )

    attempt_query = MagicMock()
    attempt_query.filter.return_value.order_by.return_value.first.return_value = None

    case_query = MagicMock()
    case_query.filter.return_value.first.return_value = case

    db = MagicMock()

    def query_side_effect(model):
        if model is RecoveryAttempt:
            return attempt_query

        if model is RecoveryCase:
            return case_query

        return MagicMock()

    db.query.side_effect = query_side_effect

    with patch("app.state.attempts.utc_now"):
        attempt = create_recovery_attempt(
            context=context,
            decision=decision,
            db=db,
        )

    assert attempt.attempt_number == 2
    assert case.current_attempt == 2
