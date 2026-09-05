from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.worker import recovery_scheduler


def test_get_due_recovery_attempts_only_returns_due_approved_attempts():
    db = MagicMock()

    attempts = [
        SimpleNamespace(
            id=1,
            status="approved",
            policy_result="approved",
        ),
    ]

    query = db.query.return_value

    (
        query
        .filter.return_value
        .filter.return_value
        .order_by.return_value
        .limit.return_value
        .all.return_value
    ) = attempts

    with patch.object(
        recovery_scheduler,
        "utc_now",
        return_value=recovery_scheduler.utc_now(),
    ):
        result = recovery_scheduler.get_due_recovery_attempts(
            db,
            limit=10,
        )

    assert result == attempts


def test_future_scheduled_attempt_is_not_executed():
    db = MagicMock()

    future_attempt = SimpleNamespace(
        id=1,
        status="approved",
        policy_result="approved",
        scheduled_at=recovery_scheduler.utc_now()
        + timedelta(minutes=30),
        action="send_payment_link",
        channel="email",
        case_id="case_future",
    )

    query = db.query.return_value

    (
        query
        .filter.return_value
        .filter.return_value
        .order_by.return_value
        .limit.return_value
        .all.return_value
    ) = []

    with patch.object(
        recovery_scheduler,
        "execute_recovery_attempt",
    ) as execute_attempt:
        result = recovery_scheduler.process_due_recovery_attempts(
            db,
            limit=10,
        )

    assert result == 0
    execute_attempt.assert_not_called()


def test_due_approved_attempt_is_executed():
    db = MagicMock()

    attempt = SimpleNamespace(
        id=42,
        status="approved",
        policy_result="approved",
        scheduled_at=recovery_scheduler.utc_now()
        - timedelta(minutes=1),
        action="send_payment_link",
        channel="email",
        case_id="case_due",
    )

    query = db.query.return_value

    (
        query
        .filter.return_value
        .filter.return_value
        .order_by.return_value
        .limit.return_value
        .all.return_value
    ) = [attempt]

    with patch.object(
        recovery_scheduler,
        "execute_recovery_attempt",
        return_value=attempt,
    ) as execute_attempt:
        result = recovery_scheduler.process_due_recovery_attempts(
            db,
            limit=10,
        )

    assert result == 1

    execute_attempt.assert_called_once_with(
        attempt=attempt,
        db=db,
    )


def test_scheduler_does_not_execute_terminal_attempts():
    db = MagicMock()

    query = db.query.return_value

    (
        query
        .filter.return_value
        .filter.return_value
        .order_by.return_value
        .limit.return_value
        .all.return_value
    ) = []

    with patch.object(
        recovery_scheduler,
        "execute_recovery_attempt",
    ) as execute_attempt:
        result = recovery_scheduler.process_due_recovery_attempts(
            db,
            limit=10,
        )

    assert result == 0
    execute_attempt.assert_not_called()


def test_scheduler_does_not_execute_attempt_for_terminal_case():
    db = MagicMock()

    attempt = SimpleNamespace(
        id=55,
        status="approved",
        policy_result="approved",
        scheduled_at=recovery_scheduler.utc_now()
        - timedelta(minutes=1),
        action="send_payment_link",
        channel="email",
        case_id="case_recovered",
    )

    recovery_case = SimpleNamespace(
        case_id="case_recovered",
        status="recovered",
    )

    # --------------------------------------------------
    # Mock the due-attempt query.
    # --------------------------------------------------

    attempt_query = MagicMock()

    (
        attempt_query
        .filter.return_value
        .filter.return_value
        .order_by.return_value
        .limit.return_value
        .all.return_value
    ) = [attempt]

    # --------------------------------------------------
    # Mock the case lookup.
    #
    # The scheduler performs:
    #
    # db.query(RecoveryCase)
    #    .filter(...)
    #    .first()
    # --------------------------------------------------

    case_query = MagicMock()
    case_query.filter.return_value.first.return_value = recovery_case

    db.query.side_effect = [
        attempt_query,
        case_query,
    ]

    with patch.object(
        recovery_scheduler,
        "execute_recovery_attempt",
    ) as execute_attempt:
        result = recovery_scheduler.process_due_recovery_attempts(
            db,
            limit=10,
        )

    assert result == 0

    execute_attempt.assert_not_called()

def test_scheduler_does_not_execute_attempt_for_escalated_case():
    db = MagicMock()

    attempt = SimpleNamespace(
        id=56,
        status="approved",
        policy_result="approved",
        scheduled_at=recovery_scheduler.utc_now()
        - timedelta(minutes=1),
        action="send_payment_link",
        channel="email",
        case_id="case_escalated",
    )

    recovery_case = SimpleNamespace(
        case_id="case_escalated",
        status="escalated",
    )

    attempt_query = MagicMock()

    (
        attempt_query
        .filter.return_value
        .filter.return_value
        .order_by.return_value
        .limit.return_value
        .all.return_value
    ) = [attempt]

    case_query = MagicMock()
    case_query.filter.return_value.first.return_value = recovery_case

    db.query.side_effect = [
        attempt_query,
        case_query,
    ]

    with patch.object(
        recovery_scheduler,
        "execute_recovery_attempt",
    ) as execute_attempt:
        result = recovery_scheduler.process_due_recovery_attempts(
            db,
            limit=10,
        )

    assert result == 0

    execute_attempt.assert_not_called()
