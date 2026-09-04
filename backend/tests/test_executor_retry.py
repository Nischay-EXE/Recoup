from unittest.mock import MagicMock, patch

import pytest

from app.state.executor import execute_recovery_attempt

def test_transient_executor_failure_does_not_create_new_attempt():
    attempt = MagicMock()
    attempt.id = 456
    attempt.event_id = "evt_retry_same_attempt"
    attempt.action = "send_payment_link"
    attempt.channel = "email"
    attempt.status = "approved"
    attempt.resolved_at = None
    attempt.execution_provider = None
    attempt.execution_error = None

    decision = MagicMock()
    decision.action = "send_payment_link"
    decision.channel = "email"

    db = MagicMock()
    decision_query = MagicMock()
    decision_query.filter.return_value.first.return_value = decision
    db.query.return_value = decision_query

    transient_error = RuntimeError("Temporary provider failure")

    with (
        patch(
            "app.state.executor.build_recovery_context",
            return_value=MagicMock(),
        ),
        patch(
            "app.state.executor.execute_strategy",
            side_effect=transient_error,
        ),
    ):
        with pytest.raises(
            RuntimeError,
            match="Temporary provider failure",
        ):
            execute_recovery_attempt(
                attempt=attempt,
                db=db,
            )

    assert attempt.id == 456
    assert attempt.status == "execution_failed"
    assert attempt.resolved_at is None
    assert attempt.execution_provider == "executor_agent"
    assert attempt.execution_error == "Temporary provider failure"

    # Executor retries the same persisted attempt.
    # It must never create a replacement attempt here.
    assert attempt.id == 456

    db.refresh.assert_called_with(attempt)
    assert db.commit.call_count >= 1

def test_transient_executor_failure_keeps_same_attempt_retryable():
    attempt = MagicMock()
    attempt.id = 123
    attempt.event_id = "evt_retry_test"
    attempt.action = "send_payment_link"
    attempt.channel = "email"
    attempt.status = "execution_failed"
    attempt.resolved_at = None
    attempt.execution_provider = None
    attempt.execution_error = None

    decision = MagicMock()
    decision.action = "send_payment_link"
    decision.channel = "email"

    db = MagicMock()

    decision_query = MagicMock()
    decision_query.filter.return_value.first.return_value = decision
    db.query.return_value = decision_query

    transient_error = RuntimeError("Temporary email provider failure")

    with (
        patch(
            "app.state.executor.build_recovery_context",
            return_value=MagicMock(),
        ),
        patch(
            "app.state.executor.execute_strategy",
            side_effect=transient_error,
        ) as execute_strategy,
    ):
        with pytest.raises(RuntimeError, match="Temporary email provider failure"):
            execute_recovery_attempt(
                attempt=attempt,
                db=db,
            )

    # The same attempt remains the retry unit.
    assert attempt.id == 123

    # Transient execution failure is explicitly retryable.
    assert attempt.status == "execution_failed"
    assert attempt.resolved_at is None
    assert attempt.execution_provider == "executor_agent"
    assert attempt.execution_error == "Temporary email provider failure"

    # The external Executor was actually attempted once.
    execute_strategy.assert_called_once()

    # The failure was persisted before the exception was propagated.
    assert db.commit.call_count >= 2
    db.refresh.assert_called_with(attempt)
