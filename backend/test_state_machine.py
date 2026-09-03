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