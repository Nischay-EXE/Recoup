from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.worker import recovery_worker


def test_process_event_rejects_before_creating_attempt():
    event_id = "evt_guardrail_worker_test"

    normalized = SimpleNamespace(
        event_id=event_id,
        event_type="payment.failed",
    )

    context = SimpleNamespace()

    decision = SimpleNamespace(
        action="send_payment_link",
        channel="whatsapp",
        confidence=0.95,
        id="decision_guardrail_test",
        reason="Unsupported real execution channel.",
    )

    normalized_query = MagicMock()
    normalized_query.filter.return_value.first.return_value = normalized

    db = MagicMock()
    db.query.return_value = normalized_query

    rejected_reason = (
        "Recovery action/channel combination is not "
        "currently supported for real execution. "
        "Payment Link execution currently supports email and sms only."
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
            "create_recovery_decision",
            return_value=decision,
        ),
        patch.object(
            recovery_worker,
            "validate_recovery_decision",
            return_value=(False, rejected_reason),
        ),
        patch.object(
            recovery_worker,
            "create_recovery_attempt",
        ) as create_attempt,
        patch.object(
            recovery_worker,
            "execute_recovery_attempt",
        ) as execute_attempt,
    ):
        recovery_worker.process_event(event_id)

    # Rejected decisions must not consume a recovery attempt.
    create_attempt.assert_not_called()

    # Rejected decisions must never reach the Executor.
    execute_attempt.assert_not_called()

    # No attempt means there is nothing to persist.
    db.commit.assert_not_called()
    db.refresh.assert_not_called()

    db.close.assert_called_once()
