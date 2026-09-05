import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.webhooks import razorpay_webhook


def test_duplicate_webhook_event_is_not_reprocessed():
    event_id = "evt_duplicate_test_001"

    payload = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_duplicate_test_001",
                    "amount": 10000,
                    "currency": "INR",
                    "status": "failed",
                    "email": "test@example.com",
                    "contact": "+919999999999",
                }
            }
        },
    }

    request = MagicMock()
    request.body = AsyncMock(
        return_value=b'{"event":"payment.failed"}'
    )
    request.json = AsyncMock(
        return_value=payload
    )

    db = MagicMock()

    existing_event = MagicMock()

    db.query.return_value.filter.return_value.first.return_value = (
        existing_event
    )

    with (
        patch(
            "app.api.webhooks.settings.razorpay_webhook_secret",
            None,
        ),
        patch(
            "app.api.webhooks.publish_recovery_event"
        ) as publish_event,
    ):
        result = asyncio.run(
            razorpay_webhook(
                request=request,
                db=db,
                x_razorpay_signature=None,
                x_razorpay_event_id=event_id,
            )
        )

    assert result == {
        "status": "duplicate",
        "event_id": event_id,
    }

    db.add.assert_not_called()
    db.commit.assert_not_called()
    publish_event.assert_not_called()

    request.body.assert_awaited_once()

