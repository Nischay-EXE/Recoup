from unittest.mock import patch

from app.worker import recovery_worker


def test_max_retries_exhaust_execution_and_acknowledge_message():
    message_id = "456-0"
    event_id = "evt_exhaustion_test"

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
            return_value=recovery_worker.MAX_MESSAGE_RETRIES,
        ),
        patch.object(
            recovery_worker,
            "_mark_execution_exhausted",
        ) as mark_exhausted,
        patch.object(
            recovery_worker,
            "acknowledge_recovery_event",
        ) as acknowledge,
    ):
        recovery_worker.handle_event(
            message_id=message_id,
            data={"event_id": event_id},
        )

    mark_exhausted.assert_called_once_with(
        event_id=event_id,
        error=str(transient_error),
    )

    acknowledge.assert_called_once_with(
        recovery_worker.CONSUMER_GROUP,
        message_id,
    )
