from unittest.mock import patch

from app.worker import recovery_worker


def test_transient_failure_does_not_ack_redis_message():
    message_id = "123-0"
    event_id = "evt_retry_test"

    transient_error = RuntimeError(
        "Temporary executor provider failure"
    )

    with (
        patch.object(
            recovery_worker,
            "process_event",
            side_effect=transient_error,
        ),
        patch.object(
            recovery_worker,
            "_get_message_delivery_count",
            return_value=1,
        ),
        patch.object(
            recovery_worker,
            "acknowledge_recovery_event",
        ) as acknowledge,
    ):
        recovery_worker.handle_event(
            message_id=message_id,
            data={"event_id": event_id},
        )

    # A transient failure below the retry limit must remain pending.
    acknowledge.assert_not_called()
