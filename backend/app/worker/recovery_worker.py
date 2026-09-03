from app.utils.time import utc_now

import os
import socket
from datetime import datetime
from decimal import Decimal
from app.db.models import Event
from app.db.recovery_models import RecoveryAttempt
from app.db.database import SessionLocal
from app.db.normalized_models import NormalizedEvent

from app.queue.redis import (
    acknowledge_recovery_event,
    claim_pending_recovery_events,
    ensure_consumer_group,
    read_recovery_events,
)

from app.state.correlation import find_recovery_attempt

from app.state.outcomes import (
    mark_recovery_succeeded,
    mark_recovery_failed,
)

from app.state.attempts import create_recovery_attempt
from app.state.context_service import build_recovery_context
from app.state.service import create_recovery_decision
from app.state.guardrail import validate_recovery_decision
from app.state.executor import execute_recovery_attempt


CONSUMER_GROUP = "recovery-workers"

CONSUMER_NAME = os.getenv(
    "WORKER_NAME",
    socket.gethostname(),
)

PENDING_IDLE_MS = 30_000
MAX_MESSAGE_RETRIES = 5


# ==========================================================
# EVENT CLASSIFICATION
# ==========================================================

RECOVERABLE_EVENTS = {
    "payment_failed",
    "payment.failed",
}

OUTCOME_EVENTS = {
    "payment_captured",
    "payment.captured",
    "payment_authorized",
    "payment.authorized",
    "order_paid",
    "order.paid",
}

NON_RECOVERY_EVENTS = {
    "payment_link.cancelled",
    "payment_link_cancelled",
    "payment_link.expired",
    "payment_link_expired",
    "payment_link.paid",
    "payment_link_paid",
}


# ==========================================================
# SUCCESSFUL PAYMENT
# ==========================================================

def process_captured_event(
    normalized: NormalizedEvent,
    db,
) -> None:
    """
    Handle a successful payment event.

    Correlation priority:
    1. recovery_attempt_id from Razorpay notes
    2. recovery_case_id from Razorpay notes
    3. payment_id
    4. order_id
    5. customer_id

    This does not invoke the AI recovery pipeline.
    It deterministically correlates the payment to a
    RecoveryAttempt and marks it successful.
    """

    # --------------------------------------------------
    # 1. Load raw Razorpay event
    # --------------------------------------------------

    source_event = (
        db.query(Event)
        .filter(
            Event.event_id == normalized.event_id
        )
        .first()
    )

    recovery_attempt_id = None
    recovery_case_id = None

    if source_event and source_event.payload:
        payment_entity = (
            source_event.payload
            .get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )

        notes = payment_entity.get("notes") or {}

        recovery_attempt_id = notes.get(
            "recovery_attempt_id"
        )

        recovery_case_id = notes.get(
            "recovery_case_id"
        )

        # --------------------------------------------------
        # Payment Links may also carry the recovery attempt
        # through reference_id:
        #
        #     rr-attempt-66
        #
        # Use this only as a fallback.
        # --------------------------------------------------

        if recovery_attempt_id is None:
            reference_id = payment_entity.get(
                "reference_id"
            )

            if (
                isinstance(reference_id, str)
                and reference_id.startswith("rr-attempt-")
            ):
                recovery_attempt_id = (
                    reference_id.removeprefix(
                        "rr-attempt-"
                    )
                )

    print(
        f"[WORKER] Outcome recovery lineage "
        f"event={normalized.event_id} "
        f"recovery_attempt_id={recovery_attempt_id} "
        f"recovery_case_id={recovery_case_id}"
    )

    # --------------------------------------------------
    # 2. Correlate recovery attempt
    # --------------------------------------------------

    attempt = find_recovery_attempt(
        db,
        recovery_attempt_id=recovery_attempt_id,
        recovery_case_id=recovery_case_id,
        payment_id=normalized.payment_id,
        order_id=normalized.order_id,
        customer_id=normalized.customer_id,
    )

    if attempt is None:
        print(
            f"[WORKER] Captured payment has no "
            f"unambiguous recovery match "
            f"event={normalized.event_id} "
            f"payment_id={normalized.payment_id} "
            f"order_id={normalized.order_id} "
            f"customer_id={normalized.customer_id}"
        )
        return

    print(
        f"[WORKER] Recovery correlated "
        f"event={normalized.event_id} "
        f"attempt_id={attempt.id} "
        f"payment_id={normalized.payment_id} "
        f"order_id={normalized.order_id}"
    )

    # --------------------------------------------------
    # 3. Only an awaiting recovery can transition to
    #    succeeded.
    #
    # Duplicate payment.captured events are therefore
    # safely ignored after the first successful transition.
    # --------------------------------------------------

    if attempt.status != "sent":
        print(
            f"[WORKER] Recovery attempt is not awaiting outcome "
            f"attempt_id={attempt.id} "
            f"status={attempt.status}"
        )
        return

    recovered_amount = normalized.amount or Decimal("0.00")

    attempt = mark_recovery_succeeded(
        attempt,
        db,
        recovered_amount,
    )

    print(
        f"[WORKER] Recovery succeeded "
        f"attempt_id={attempt.id} "
        f"amount_recovered={attempt.amount_recovered}"
    )


# ==========================================================
# FAILED PAYMENT
# ==========================================================

def process_failed_event(
    normalized: NormalizedEvent,
    db,
) -> None:
    """
    Resolve the currently active recovery attempt when the
    payment that was being recovered has failed again.
    """

    attempt = find_recovery_attempt(
        db,
        payment_id=normalized.payment_id,
        order_id=normalized.order_id,
        customer_id=normalized.customer_id,
    )

    if attempt is None:
        print(
            f"[WORKER] Failed payment has no "
            f"matching active recovery attempt "
            f"event={normalized.event_id} "
            f"payment_id={normalized.payment_id} "
            f"order_id={normalized.order_id}"
        )
        return

    if attempt.status != "sent":
        print(
            f"[WORKER] Failed payment is not associated with "
            f"an awaiting recovery attempt "
            f"attempt_id={attempt.id} "
            f"status={attempt.status}"
        )
        return

    mark_recovery_failed(
        attempt,
        db,
    )

    print(
        f"[WORKER] Previous recovery attempt failed "
        f"attempt_id={attempt.id} "
        f"payment_id={normalized.payment_id} "
        f"order_id={normalized.order_id}"
    )


# ==========================================================
# NON-RECOVERY EVENTS
# ==========================================================

def process_non_recovery_event(
    normalized: NormalizedEvent,
) -> None:
    """
    Handle events that should be acknowledged but must not
    enter the AI recovery pipeline.

    Example:
        payment_link.cancelled

    A customer cancelling a payment link is not itself a
    failed payment recovery attempt.
    """

    print(
        f"[WORKER] Non-recovery event received "
        f"event={normalized.event_id} "
        f"event_type={normalized.event_type} "
        f"payment_id={normalized.payment_id} "
        f"order_id={normalized.order_id}"
    )

    print(
        f"[WORKER] Skipping recovery pipeline "
        f"event={normalized.event_id} "
        f"reason=event_type_not_recoverable"
    )


# ==========================================================
# MAIN EVENT PROCESSOR
# ==========================================================

def process_event(event_id: str):
    db = SessionLocal()

    try:
        # --------------------------------------------------
        # 1. Verify normalized event exists
        # --------------------------------------------------

        normalized = (
            db.query(NormalizedEvent)
            .filter(
                NormalizedEvent.event_id == event_id
            )
            .first()
        )

        if normalized is None:
            raise ValueError(
                f"Normalized event not found: {event_id}"
            )

        # --------------------------------------------------
        # 2. Events that should NOT enter recovery
        # --------------------------------------------------

        if normalized.event_type in NON_RECOVERY_EVENTS:
            process_non_recovery_event(
                normalized=normalized,
            )
            return

        # --------------------------------------------------
        # 3. Handle successful payment outcomes
        # --------------------------------------------------

        if normalized.event_type in OUTCOME_EVENTS:
            process_captured_event(
                normalized=normalized,
                db=db,
            )
            return

        # --------------------------------------------------
        # 4. Only recoverable events enter the AI pipeline
        # --------------------------------------------------

        if normalized.event_type not in RECOVERABLE_EVENTS:
            print(
                f"[WORKER] Unhandled event type "
                f"event={normalized.event_id} "
                f"event_type={normalized.event_type} "
                f"Skipping recovery pipeline."
            )
            return

        # --------------------------------------------------
        # 5. Resolve any prior active recovery attempt
        #    for this payment (marks it as failed)
        # --------------------------------------------------

        process_failed_event(
            normalized=normalized,
            db=db,
        )

        # --------------------------------------------------
        # 6. Build context from PostgreSQL
        # --------------------------------------------------

        context = build_recovery_context(
            event_id=event_id,
            db=db,
        )

        # --------------------------------------------------
        # 7. Create / retrieve recovery decision
        # --------------------------------------------------

        decision = create_recovery_decision(
            context=context,
            db=db,
        )

        # --------------------------------------------------
        # 8. Policy Guardrail
        #
        # IMPORTANT:
        # Run the guardrail BEFORE creating a RecoveryAttempt.
        #
        # A rejected AI decision must not consume case-level
        # recovery attempt capacity.
        # --------------------------------------------------

        approved, policy_reason = validate_recovery_decision(
            context=context,
            decision=decision,
        )

        print(
            f"[WORKER] Guardrail "
            f"event={event_id} "
            f"approved={approved} "
            f"reason={policy_reason}"
        )

        if not approved:
            print(
                f"[WORKER] Recovery decision rejected "
                f"before attempt creation "
                f"event={event_id} "
                f"reason={policy_reason}"
            )

            return

        # --------------------------------------------------
        # 9. Create / retrieve recovery attempt
        # --------------------------------------------------

        # `no_action` is a decision, not a recovery attempt.
        # Do not create a RecoveryAttempt for it, otherwise it inflates
        # case.current_attempt and eventually distorts the attempt limit.
        attempt = None
        skip_execution = True

        terminal_statuses = {
            "succeeded",
            "failed",
            "stopped",
            "escalated",
            "blocked",
            "execution_exhausted",
        }

        successful_attempt = (
            db.query(RecoveryAttempt)
            .filter(
                RecoveryAttempt.event_id == event_id,
                RecoveryAttempt.status == "succeeded",
            )
            .order_by(
                RecoveryAttempt.attempt_number.desc()
            )
            .first()
        )

        if decision.action == "no_action":
            print(
                f"[WORKER] No recovery attempt created "
                f"event={event_id} "
                f"reason=decision_no_action"
            )

        elif successful_attempt:
            attempt = successful_attempt

            print(
                f"[WORKER] Recovery already succeeded "
                f"event={event_id} "
                f"attempt_id={attempt.id} "
                f"amount_recovered={attempt.amount_recovered} "
                f"Skipping duplicate recovery."
            )

            skip_execution = True

        else:
            latest_attempt = (
                db.query(RecoveryAttempt)
                .filter(
                    RecoveryAttempt.event_id == event_id
                )
                .order_by(
                    RecoveryAttempt.attempt_number.desc()
                )
                .first()
            )

            if (
                latest_attempt
                and latest_attempt.status in terminal_statuses
            ):
                attempt = latest_attempt

                print(
                    f"[WORKER] Terminal attempt already exists "
                    f"event={event_id} "
                    f"attempt_id={attempt.id} "
                    f"status={attempt.status} "
                    f"Skipping recovery."
                )

                skip_execution = True

            else:
                attempt = create_recovery_attempt(
                    context=context,
                    decision=decision,
                    db=db,
                )

                skip_execution = False

        # --------------------------------------------------
        # 10. Persist approved guardrail result
        # --------------------------------------------------

        if attempt is not None:
            attempt.policy_result = "approved"
            attempt.policy_reason = policy_reason

            db.commit()
            db.refresh(attempt)

        # --------------------------------------------------
        # 11. Execute approved recovery.
        #     no_action intentionally has no attempt to execute.
        # --------------------------------------------------

        if (
            approved
            and attempt is not None
            and not skip_execution
        ):
            attempt = execute_recovery_attempt(
                attempt=attempt,
                db=db,
            )

        # --------------------------------------------------
        # 12. Log successful processing
        # --------------------------------------------------

        print(
            f"[WORKER] Processed "
            f"event={event_id} "
            f"decision_id={decision.id} "
            f"attempt_id={attempt.id if attempt else None} "
            f"attempt_number={attempt.attempt_number if attempt else None} "
            f"action={decision.action} "
            f"channel={decision.channel} "
            f"confidence={decision.confidence} "
            f"reason={decision.reason} "
            f"attempt_status={attempt.status if attempt else 'not_created'}"
        )

    finally:
        db.close()


# ==========================================================
# POISON MESSAGE DETECTION
# ==========================================================

def _get_message_delivery_count(
    message_id: str,
) -> int:
    """
    Get the number of times a message has been delivered.

    Uses XPENDING to check the delivery count for the
    specific message.
    """

    from app.queue.redis import redis_client, STREAM_NAME

    pending = redis_client.xpending_range(
        STREAM_NAME,
        CONSUMER_GROUP,
        min=message_id,
        max=message_id,
        count=1,
    )

    if pending:
        return pending[0].get(
            "times_delivered", 0
        )

    return 0


def _mark_execution_exhausted(
    event_id: str,
    error: str,
) -> None:
    """Persist a terminal execution failure before ACKing a poison message."""

    db = SessionLocal()

    try:
        attempt = (
            db.query(RecoveryAttempt)
            .filter(
                RecoveryAttempt.event_id == event_id,
                RecoveryAttempt.status.in_(
                    {"approved", "execution_failed"}
                ),
            )
            .order_by(
                RecoveryAttempt.attempt_number.desc()
            )
            .first()
        )

        if attempt is None:
            return

        attempt.status = "execution_exhausted"
        attempt.execution_provider = "executor_agent"
        attempt.execution_error = (
            f"Maximum Redis delivery retries exhausted: {error}"
        )
        attempt.resolved_at = utc_now()

        db.commit()
        db.refresh(attempt)

        print(
            f"[WORKER] Execution retries exhausted "
            f"event={event_id} "
            f"attempt_id={attempt.id} "
            f"status={attempt.status}"
        )

    finally:
        db.close()


# ==========================================================
# REDIS MESSAGE HANDLER
# ==========================================================

def handle_event(
    message_id: str,
    data: dict[str, str],
) -> None:

    event_id = data.get("event_id")

    # --------------------------------------------------
    # Invalid Redis message
    # --------------------------------------------------

    if not event_id:
        print(
            f"[WORKER] Missing event_id "
            f"in message {message_id}"
        )

        acknowledge_recovery_event(
            CONSUMER_GROUP,
            message_id,
        )

        return

    # --------------------------------------------------
    # Process event
    # --------------------------------------------------

    try:
        process_event(event_id)

        # ACK only after successful processing
        acknowledge_recovery_event(
            CONSUMER_GROUP,
            message_id,
        )

        print(
            f"[WORKER] ACK "
            f"message={message_id}"
        )

    except Exception as exc:
        # --------------------------------------------------
        # Poison-message protection
        #
        # After MAX_MESSAGE_RETRIES failures the message is
        # acknowledged to prevent infinite reclaim loops.
        # The error is logged for investigation.
        # --------------------------------------------------

        print(
            f"[WORKER] Failed "
            f"message={message_id}: {exc}"
        )

        try:
            info = _get_message_delivery_count(
                message_id,
            )

            if info >= MAX_MESSAGE_RETRIES:
                print(
                    f"[WORKER] Poison message detected "
                    f"message={message_id} "
                    f"deliveries={info} "
                    f"ACKing to break reclaim loop."
                )

                _mark_execution_exhausted(
                    event_id=event_id,
                    error=str(exc),
                )

                acknowledge_recovery_event(
                    CONSUMER_GROUP,
                    message_id,
                )

        except Exception:
            pass


# ==========================================================
# WORKER LOOP
# ==========================================================

def run_worker() -> None:

    print(
        f"Recovery worker started: "
        f"{CONSUMER_NAME}"
    )

    # --------------------------------------------------
    # Ensure Redis consumer group exists
    # --------------------------------------------------

    ensure_consumer_group(
        CONSUMER_GROUP
    )

    print(
        f"Consumer group ready: "
        f"{CONSUMER_GROUP}"
    )

    # --------------------------------------------------
    # Main worker loop
    # --------------------------------------------------

    while True:

        # --------------------------------------------------
        # 1. Recover old pending messages
        # --------------------------------------------------

        pending_events = claim_pending_recovery_events(
            consumer_group=CONSUMER_GROUP,
            consumer_name=CONSUMER_NAME,
            min_idle_ms=PENDING_IDLE_MS,
            count=10,
        )

        for message_id, data in pending_events:

            print(
                f"[WORKER] Reclaimed pending "
                f"message={message_id}"
            )

            handle_event(
                message_id,
                data,
            )

        # --------------------------------------------------
        # 2. Process new messages
        # --------------------------------------------------

        new_events = read_recovery_events(
            consumer_group=CONSUMER_GROUP,
            consumer_name=CONSUMER_NAME,
            count=1,
            block_ms=5000,
        )

        for message_id, data in new_events:

            handle_event(
                message_id,
                data,
            )


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":
    run_worker()