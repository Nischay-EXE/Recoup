from app.utils.time import utc_now
import hashlib
import hmac
from datetime import datetime
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
)
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.db.models import Event
from app.db.normalized_models import NormalizedEvent
from app.normalization.razorpay import normalize_razorpay_event
from app.queue.redis import publish_recovery_event
from app.state.history_service import sync_razorpay_history
from app.state.batch_service import get_active_batch


router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
)


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_razorpay_signature: str | None = Header(default=None),
    x_razorpay_event_id: str | None = Header(default=None),
) -> dict[str, Any]:

    # ==================================================
    # 1. Read the RAW request body
    # ==================================================

    raw_body = await request.body()

    # DEBUG:
    # Show exactly what Razorpay sent before parsing
    # and normalization.
    print("\n" + "=" * 100)
    print("[RAZORPAY RAW WEBHOOK]")

    try:
        print(raw_body.decode("utf-8"))
    except UnicodeDecodeError:
        print(raw_body)

    print("=" * 100 + "\n")

    # ==================================================
    # 2. Verify Razorpay webhook signature
    # ==================================================

    webhook_secret = settings.razorpay_webhook_secret

    if webhook_secret:
        if not x_razorpay_signature:
            raise HTTPException(
                status_code=400,
                detail="Missing Razorpay webhook signature",
            )

        expected_signature = hmac.new(
            webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(
            expected_signature,
            x_razorpay_signature,
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid Razorpay webhook signature",
            )

    # ==================================================
    # 3. Parse JSON payload
    # ==================================================

    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload",
        )

    # ==================================================
    # 4. Get Razorpay event ID
    # ==================================================

    event_id = (
        x_razorpay_event_id
        or payload.get("event_id")
    )

    if not event_id:
        raise HTTPException(
            status_code=400,
            detail="Missing Razorpay event ID",
        )

    event_type = payload.get(
        "event",
        "unknown",
    )

    active_batch = get_active_batch(db)

    # ==================================================
    # 5. Check for duplicate event
    # ==================================================

    existing_event = (
        db.query(Event)
        .filter(
            Event.event_id == event_id
        )
        .first()
    )

    if existing_event:
        print(
            f"[WEBHOOK] Duplicate event ignored "
            f"event_id={event_id}"
        )

        return {
            "status": "duplicate",
            "event_id": event_id,
        }

    # ==================================================
    # 6. Store RAW Razorpay event
    # ==================================================

    event = Event(
        source="razorpay",
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        batch_id=(active_batch.batch_id if active_batch else None),
    )

    db.add(event)

    # ==================================================
    # 7. Normalize Razorpay event
    # ==================================================

    normalized = normalize_razorpay_event(
        payload=payload,
        event_id=event_id,
        received_at=utc_now(),
    )

    # ==================================================
    # 8. Sync Customer / Order / Payment history
    #
    # This populates:
    #
    #   customers
    #   orders
    #   payments
    #
    # The complete original webhook remains stored in:
    #
    #   events.payload
    #
    # payment_link.cancelled and other events that do not
    # contain payment/order data simply return an empty
    # HistorySyncResult.
    # ==================================================

    history = sync_razorpay_history(
        payload=payload,
        db=db,
    )

    # ==================================================
    # 9. Store normalized event
    #
    # Prefer IDs resolved by history_service.
    # Fall back to values extracted directly by the
    # normalizer.
    # ==================================================

    normalized_record = NormalizedEvent(
        event_id=normalized.event_id,
        source=normalized.source,
        event_type=normalized.event_type,
        batch_id=(active_batch.batch_id if active_batch else None),

        customer_id=(
            history.customer_id
            or normalized.customer_id
        ),

        payment_id=(
            history.payment_id
            or normalized.payment_id
        ),

        order_id=(
            history.order_id
            or normalized.order_id
        ),

        subscription_id=normalized.subscription_id,

        invoice_id=normalized.invoice_id,

        amount=normalized.amount,
        currency=normalized.currency,
        status=normalized.status,
        occurred_at=normalized.occurred_at,
        received_at=normalized.received_at,
    )

    db.add(normalized_record)

    # ==================================================
    # 10. Commit all database changes together
    #
    # This commits:
    #
    #   Event
    #   Customer
    #   Order
    #   Payment
    #   NormalizedEvent
    #
    # as one database transaction.
    # ==================================================

    db.commit()

    db.refresh(event)
    db.refresh(normalized_record)

    # ==================================================
    # 11. Publish normalized event to Redis Stream
    # ==================================================

    message_id = publish_recovery_event(
        event_id=normalized.event_id,
    )

    # ==================================================
    # 12. Log synchronization result
    # ==================================================

    print(
        f"[WEBHOOK] Processed Razorpay event "
        f"event_id={event_id} "
        f"event_type={event_type} "
        f"customer_id={history.customer_id} "
        f"payment_id={history.payment_id} "
        f"order_id={history.order_id} "
        f"subscription_id={normalized.subscription_id} "
        f"invoice_id={normalized.invoice_id}"
    )

    print(
        f"[WEBHOOK] Redis queued "
        f"event_id={normalized.event_id} "
        f"message_id={message_id}"
    )

    # ==================================================
    # 13. Return
    # ==================================================

    return {
        "status": "queued",
        "event_id": event_id,
        "normalized_event_id": normalized_record.id,
        "message_id": message_id,
        "customer_id": history.customer_id,
        "payment_id": history.payment_id,
        "order_id": history.order_id,
        "subscription_id": normalized.subscription_id,
        "invoice_id": normalized.invoice_id,
    }
