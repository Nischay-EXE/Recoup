import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from app.db.database import SessionLocal
from app.db.models import Event
from app.db.normalized_models import NormalizedEvent
from app.db.recovery_models import RecoveryAttempt, RecoveryCase, RecoveryDecisionRecord
from app.utils.time import utc_now
from app.worker.recovery_worker import process_event


def _add_invoice_event(
    db,
    *,
    event_id: str,
    invoice_id: str,
    customer_id: str,
    event_type: str,
    amount_paid: Decimal,
    amount_due: Decimal,
):
    db.add(
        Event(
            source="razorpay",
            event_id=event_id,
            event_type=event_type,
            payload={
                "event": event_type,
                "payload": {
                    "invoice": {
                        "entity": {
                            "id": invoice_id,
                            "customer_id": customer_id,
                            "amount": 25000,
                            "amount_paid": int(amount_paid * 100),
                            "amount_due": int(amount_due * 100),
                            "currency": "INR",
                            "status": (
                                "paid"
                                if amount_due == Decimal("0.00")
                                else "partially_paid"
                            ),
                        }
                    }
                },
            },
        )
    )

    db.add(
        NormalizedEvent(
            event_id=event_id,
            source="razorpay",
            event_type=(
                "invoice_paid"
                if event_type == "invoice.paid"
                else "invoice_partially_paid"
            ),
            customer_id=customer_id,
            payment_id=None,
            order_id=None,
            subscription_id=None,
            invoice_id=invoice_id,
            amount=Decimal("250.00"),
            amount_paid=amount_paid,
            amount_due=amount_due,
            currency="INR",
            status=(
                "paid"
                if amount_due == Decimal("0.00")
                else "partially_paid"
            ),
        )
    )
    db.commit()


def test_partial_invoice_payment_opens_case_and_runs_recovery_pipeline():
    db = SessionLocal()

    invoice_id = f"inv_partial_e2e_{uuid.uuid4().hex}"
    customer_id = f"cust_partial_e2e_{uuid.uuid4().hex}"
    event_id = f"evt_partial_e2e_{uuid.uuid4().hex}"

    try:
        _add_invoice_event(
            db,
            event_id=event_id,
            invoice_id=invoice_id,
            customer_id=customer_id,
            event_type="invoice.partially_paid",
            amount_paid=Decimal("100.00"),
            amount_due=Decimal("150.00"),
        )

        decision = RecoveryDecisionRecord(
            event_id=event_id,
            action="send_payment_link",
            channel="email",
            reason="Invoice remains partially unpaid.",
            message="Please complete the remaining invoice balance.",
            confidence=0.9,
            priority="high",
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)

        with patch(
            "app.worker.recovery_worker.create_recovery_decision",
            return_value=decision,
        ), patch(
            "app.worker.recovery_worker.execute_recovery_attempt"
        ) as execute:
            def execute_attempt(attempt, db):
                attempt.status = "sent"
                attempt.executed_at = utc_now()
                db.commit()
                db.refresh(attempt)
                return attempt

            execute.side_effect = execute_attempt

            process_event(event_id)

        case = (
            db.query(RecoveryCase)
            .filter(RecoveryCase.invoice_id == invoice_id)
            .one()
        )

        attempt = (
            db.query(RecoveryAttempt)
            .filter(RecoveryAttempt.event_id == event_id)
            .one()
        )

        assert case.revenue_object_type == "invoice"
        assert case.amount_at_risk == Decimal("250.00")
        assert case.amount_recovered == Decimal("100.00")
        assert case.status == "open"
        assert attempt.amount_at_risk == Decimal("150.00")
        assert attempt.action == "send_payment_link"
        assert attempt.status == "sent"

    finally:
        db.close()


def test_partial_invoice_payment_is_cumulative_and_final_payment_closes_case():
    db = SessionLocal()

    invoice_id = f"inv_partial_full_e2e_{uuid.uuid4().hex}"
    customer_id = f"cust_partial_full_e2e_{uuid.uuid4().hex}"
    first_event_id = f"evt_partial_first_{uuid.uuid4().hex}"
    second_event_id = f"evt_partial_second_{uuid.uuid4().hex}"
    paid_event_id = f"evt_partial_paid_{uuid.uuid4().hex}"

    try:
        _add_invoice_event(
            db,
            event_id=first_event_id,
            invoice_id=invoice_id,
            customer_id=customer_id,
            event_type="invoice.partially_paid",
            amount_paid=Decimal("100.00"),
            amount_due=Decimal("150.00"),
        )

        first_decision = RecoveryDecisionRecord(
            event_id=first_event_id,
            action="send_payment_link",
            channel="email",
            reason="Recover remaining invoice balance.",
            message="Please complete your remaining invoice payment.",
            confidence=0.9,
            priority="high",
        )
        db.add(first_decision)
        db.commit()
        db.refresh(first_decision)

        with patch(
            "app.worker.recovery_worker.create_recovery_decision",
            return_value=first_decision,
        ), patch(
            "app.worker.recovery_worker.execute_recovery_attempt"
        ) as execute:
            def execute_attempt(attempt, db):
                attempt.status = "sent"
                attempt.executed_at = utc_now()
                db.commit()
                db.refresh(attempt)
                return attempt

            execute.side_effect = execute_attempt
            process_event(first_event_id)

        # Duplicate cumulative webhook must not add another ₹100.
        duplicate_event_id = f"evt_partial_duplicate_{uuid.uuid4().hex}"
        _add_invoice_event(
            db,
            event_id=duplicate_event_id,
            invoice_id=invoice_id,
            customer_id=customer_id,
            event_type="invoice.partially_paid",
            amount_paid=Decimal("100.00"),
            amount_due=Decimal("150.00"),
        )

        process_event(duplicate_event_id)

        db.refresh(
            db.query(RecoveryCase)
            .filter(RecoveryCase.invoice_id == invoice_id)
            .one()
        )

        case = (
            db.query(RecoveryCase)
            .filter(RecoveryCase.invoice_id == invoice_id)
            .one()
        )
        assert case.amount_recovered == Decimal("100.00")
        assert case.status == "open"

        # Second cumulative partial payment moves recovery to ₹180.
        _add_invoice_event(
            db,
            event_id=second_event_id,
            invoice_id=invoice_id,
            customer_id=customer_id,
            event_type="invoice.partially_paid",
            amount_paid=Decimal("180.00"),
            amount_due=Decimal("70.00"),
        )

        second_decision = RecoveryDecisionRecord(
            event_id=second_event_id,
            action="send_reminder",
            channel="email",
            reason="Invoice still has an outstanding balance.",
            message="This is a reminder to complete your payment.",
            confidence=0.8,
            priority="high",
        )
        db.add(second_decision)
        db.commit()
        db.refresh(second_decision)

        with patch(
            "app.worker.recovery_worker.create_recovery_decision",
            return_value=second_decision,
        ), patch(
            "app.worker.recovery_worker.execute_recovery_attempt"
        ) as execute:
            execute.side_effect = execute_attempt
            process_event(second_event_id)

        case = (
            db.query(RecoveryCase)
            .filter(RecoveryCase.invoice_id == invoice_id)
            .one()
        )
        assert case.amount_recovered == Decimal("180.00")
        assert case.amount_at_risk == Decimal("250.00")
        assert case.status == "open"

        # Final payment must close the case even if the latest recovery
        # attempt is already sent. The attempt is correlated by invoice_id.
        _add_invoice_event(
            db,
            event_id=paid_event_id,
            invoice_id=invoice_id,
            customer_id=customer_id,
            event_type="invoice.paid",
            amount_paid=Decimal("250.00"),
            amount_due=Decimal("0.00"),
        )

        process_event(paid_event_id)

        db.refresh(case)
        assert case.amount_recovered == Decimal("250.00")
        assert case.status == "recovered"
        assert case.resolved_at is not None

    finally:
        db.close()


def test_partial_invoice_payment_with_nested_payment_uses_invoice_total():
    """Mirror Razorpay's real invoice.partially_paid payload shape."""
    db = SessionLocal()

    invoice_id = f"inv_partial_real_shape_{uuid.uuid4().hex}"
    customer_id = f"cust_partial_real_shape_{uuid.uuid4().hex}"
    event_id = f"evt_partial_real_shape_{uuid.uuid4().hex}"

    try:
        db.add(
            Event(
                source="razorpay",
                event_id=event_id,
                event_type="invoice.partially_paid",
                payload={
                    "event": "invoice.partially_paid",
                    "contains": ["payment", "order", "invoice"],
                    "payload": {
                        "payment": {
                            "entity": {
                                "id": "pay_real_shape",
                                "amount": 10000000,
                                "currency": "INR",
                                "status": "attempted",
                                "order_id": "order_real_shape",
                            }
                        },
                        "invoice": {
                            "entity": {
                                "id": invoice_id,
                                "customer_id": customer_id,
                                "order_id": "order_real_shape",
                                "payment_id": "pay_real_shape",
                                "amount": 44600000,
                                "amount_paid": 10000000,
                                "amount_due": 34600000,
                                "currency": "INR",
                                "status": "partially_paid",
                            }
                        },
                    },
                },
            )
        )

        from app.normalization.razorpay import normalize_razorpay_event

        normalized = normalize_razorpay_event(
            payload={
                "event": "invoice.partially_paid",
                "payload": {
                    "payment": {
                        "entity": {
                            "id": "pay_real_shape",
                            "amount": 10000000,
                            "currency": "INR",
                            "status": "attempted",
                            "order_id": "order_real_shape",
                        }
                    },
                    "invoice": {
                        "entity": {
                            "id": invoice_id,
                            "customer_id": customer_id,
                            "order_id": "order_real_shape",
                            "payment_id": "pay_real_shape",
                            "amount": 44600000,
                            "amount_paid": 10000000,
                            "amount_due": 34600000,
                            "currency": "INR",
                            "status": "partially_paid",
                        }
                    },
                },
            },
            event_id=event_id,
        )

        db.add(
            NormalizedEvent(
                event_id=normalized.event_id,
                source=normalized.source,
                event_type=normalized.event_type,
                customer_id=normalized.customer_id,
                payment_id=normalized.payment_id,
                order_id=normalized.order_id,
                subscription_id=normalized.subscription_id,
                invoice_id=normalized.invoice_id,
                amount=normalized.amount,
                amount_paid=normalized.amount_paid,
                amount_due=normalized.amount_due,
                currency=normalized.currency,
                status=normalized.status,
            )
        )
        db.commit()

        decision = RecoveryDecisionRecord(
            event_id=event_id,
            action="send_payment_link",
            channel="email",
            reason="Recover outstanding invoice balance.",
            message="Please complete the remaining invoice balance.",
            confidence=0.9,
            priority="high",
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)

        with patch(
            "app.worker.recovery_worker.create_recovery_decision",
            return_value=decision,
        ), patch(
            "app.worker.recovery_worker.execute_recovery_attempt"
        ) as execute:
            def execute_attempt(attempt, db):
                attempt.status = "sent"
                attempt.executed_at = utc_now()
                db.commit()
                db.refresh(attempt)
                return attempt

            execute.side_effect = execute_attempt
            process_event(event_id)

        case = (
            db.query(RecoveryCase)
            .filter(RecoveryCase.invoice_id == invoice_id)
            .one()
        )

        attempt = (
            db.query(RecoveryAttempt)
            .filter(RecoveryAttempt.event_id == event_id)
            .one()
        )

        assert case.amount_at_risk == Decimal("446000.00")
        assert case.amount_recovered == Decimal("100000.00")
        assert case.amount_at_risk - case.amount_recovered == Decimal("346000.00")
        assert case.status == "open"
        assert attempt.amount_at_risk == Decimal("346000.00")

    finally:
        db.close()
