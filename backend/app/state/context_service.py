from sqlalchemy.orm import Session

from app.db.history_models import Customer, Order, Payment
from app.db.models import Event
from app.db.normalized_models import NormalizedEvent
from app.db.recovery_models import RecoveryAttempt
from app.state.case_service import get_or_create_recovery_case, register_payment_attempt
from app.state.context import RecoveryContext


def _extract_recovery_case_id(event: Event) -> str | None:
    """Extract our recovery lineage from a Razorpay payment notes payload."""

    payload = event.payload or {}
    payment_entity = (
        payload
        .get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )
    notes = payment_entity.get("notes") or {}

    if not isinstance(notes, dict):
        return None

    case_id = notes.get("recovery_case_id")

    if not isinstance(case_id, str) or not case_id.strip():
        return None

    return case_id.strip()


def build_recovery_context(
    event_id: str,
    db: Session,
) -> RecoveryContext:

    # --------------------------------------------------
    # 1. Get current normalized event
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
    # 2. Resolve customer ID
    #
    # Prefer the normalized event.
    # If it is missing, derive it from payment/order
    # history in PostgreSQL.
    # --------------------------------------------------

    customer_id = normalized.customer_id

    if customer_id is None and normalized.payment_id:

        payment = (
            db.query(Payment)
            .filter(
                Payment.payment_id == normalized.payment_id
            )
            .first()
        )

        if payment is not None:
            customer_id = payment.customer_id

    if customer_id is None and normalized.order_id:

        order = (
            db.query(Order)
            .filter(
                Order.order_id == normalized.order_id
            )
            .first()
        )

        if order is not None:
            customer_id = order.customer_id

    # --------------------------------------------------
    # 3. Get customer record
    # --------------------------------------------------

    customer = None

    if customer_id is not None:

        customer = (
            db.query(Customer)
            .filter(
                Customer.customer_id == customer_id
            )
            .first()
        )

    # --------------------------------------------------
    # 4. Get payment history
    # --------------------------------------------------

    payments = []

    if customer_id is not None:

        payments = (
            db.query(Payment)
            .filter(
                Payment.customer_id == customer_id
            )
            .order_by(
                Payment.created_at.asc()
            )
            .all()
        )

    # --------------------------------------------------
    # 5. Calculate customer payment statistics
    # --------------------------------------------------

    total_payments = len(payments)

    successful_payments = sum(
        1
        for payment in payments
        if payment.status in {
            "captured",
            "paid",
            "success",
            "successful",
        }
    )

    failed_payments = sum(
        1
        for payment in payments
        if payment.status in {
            "failed",
            "failure",
        }
    )

    # --------------------------------------------------
    # 6. Serialize payment history
    # --------------------------------------------------

    payment_history = [
        {
            "payment_id": payment.payment_id,
            "customer_id": payment.customer_id,
            "order_id": payment.order_id,
            "amount": (
                str(payment.amount)
                if payment.amount is not None
                else None
            ),
            "currency": payment.currency,
            "status": payment.status,
            "failure_reason": payment.failure_reason,
            "created_at": (
                payment.created_at.isoformat()
                if payment.created_at
                else None
            ),
        }
        for payment in payments
    ]

    # --------------------------------------------------
    # 7. Resolve the recovery case
    # --------------------------------------------------

    case = None
    recovery_attempts = []

    if normalized.event_type in {
        "payment_failed",
        "payment.failed",
        "subscription_pending",
        "subscription.pending",
        "subscription_halted",
        "subscription.halted",
    }:
        # A Razorpay Payment Link creates a new order/payment when the
        # customer retries through the link. The payment payload preserves
        # our recovery_case_id in notes, so use that explicit lineage before
        # falling back to payment/order matching.
        source_event = (
            db.query(Event)
            .filter(Event.event_id == event_id)
            .first()
        )
        recovery_case_id = (
            _extract_recovery_case_id(source_event)
            if source_event is not None
            else None
        )

        case = get_or_create_recovery_case(
        db,
        customer_id=normalized.customer_id,
        order_id=normalized.order_id,
        payment_id=normalized.payment_id,
        amount=normalized.amount,
        case_id=recovery_case_id,
        revenue_object_type=(
            "subscription"
            if normalized.subscription_id
            else "invoice"
            if normalized.invoice_id
            else "payment"
        ),
        subscription_id=normalized.subscription_id,
        invoice_id=normalized.invoice_id,
    )

        # Keep the case's current payment pointed at the newest payment
        # while preserving the original payment ID.
        if normalized.payment_id and case.current_payment_id != normalized.payment_id:
            case = register_payment_attempt(
                db,
                case,
                payment_id=normalized.payment_id,
            )

        # --------------------------------------------------
        # 8. Get recovery history for the entire case
        # --------------------------------------------------

        recovery_attempts = (
            db.query(RecoveryAttempt)
            .filter(
                RecoveryAttempt.case_id == case.case_id
            )
            .order_by(
                RecoveryAttempt.attempt_number.asc()
            )
            .all()
        )

    recovery_history = [
        {
            "id": attempt.id,
            "case_id": attempt.case_id,
            "event_id": attempt.event_id,
            "payment_id": attempt.payment_id,
            "order_id": attempt.order_id,
            "customer_id": attempt.customer_id,
            "action": attempt.action,
            "channel": attempt.channel,
            "attempt_number": attempt.attempt_number,
            "status": attempt.status,
            "amount_at_risk": (
                str(attempt.amount_at_risk)
                if attempt.amount_at_risk is not None
                else None
            ),
            "amount_recovered": (
                str(attempt.amount_recovered)
                if attempt.amount_recovered is not None
                else None
            ),
            "created_at": (
                attempt.created_at.isoformat()
                if attempt.created_at
                else None
            ),
            "executed_at": (
                attempt.executed_at.isoformat()
                if attempt.executed_at
                else None
            ),
            "resolved_at": (
                attempt.resolved_at.isoformat()
                if attempt.resolved_at
                else None
            ),
        }
        for attempt in recovery_attempts
    ]

    # --------------------------------------------------
    # 8. Build verified context
    # --------------------------------------------------

    return RecoveryContext(

        # Current event
        event_id=normalized.event_id,
        event_type=normalized.event_type,
        batch_id=normalized.batch_id,

        case_id=(case.case_id if case is not None else None),
        current_case_attempt=(
            case.current_attempt if case is not None else 0
        ),

        # Revenue object
        revenue_object_type=(
            "subscription"
            if normalized.subscription_id
            else "invoice"
            if normalized.invoice_id
            else "payment"
        ),

        payment_id=normalized.payment_id,
        order_id=normalized.order_id,
        subscription_id=normalized.subscription_id,
        invoice_id=normalized.invoice_id,

        amount=normalized.amount,
        currency=normalized.currency,
        payment_status=normalized.status,

        # Resolved customer
        customer_id=customer_id,

        # Customer history
        customer_total_payments=(
            total_payments
            if customer is not None
            else None
        ),

        customer_successful_payments=(
            successful_payments
            if customer is not None
            else None
        ),

        customer_failed_payments=(
            failed_payments
            if customer is not None
            else None
        ),

        # Payment history
        payment_history=payment_history,

        # Recovery history
        previous_attempts=len(
            recovery_attempts
        ),

        previous_recovery_attempts=recovery_history,

        # Merchant policy will be added later
        merchant_policy={},

        # Verified metadata
        metadata={
            "source": normalized.source,

            "occurred_at": (
                normalized.occurred_at.isoformat()
                if normalized.occurred_at
                else None
            ),

            "received_at": (
                normalized.received_at.isoformat()
                if normalized.received_at
                else None
            ),
        },
    )