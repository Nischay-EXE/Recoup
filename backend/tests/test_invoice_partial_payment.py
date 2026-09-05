import uuid
from decimal import Decimal

from app.db.database import SessionLocal
from app.db.normalized_models import NormalizedEvent
from app.db.recovery_models import RecoveryCase
from app.state.outcomes import record_invoice_partial_payment


def test_invoice_partial_payment_is_cumulative_and_idempotent():
    db = SessionLocal()

    invoice_id = f"inv_partial_{uuid.uuid4().hex}"
    case_id = f"case_partial_{uuid.uuid4().hex}"

    try:
        # --------------------------------------------------
        # 1. Create an open invoice recovery case
        # --------------------------------------------------

        case = RecoveryCase(
            case_id=case_id,
            customer_id=f"cust_{uuid.uuid4().hex}",
            order_id=None,
            revenue_object_type="invoice",
            subscription_id=None,
            invoice_id=invoice_id,
            original_payment_id=None,
            current_payment_id=None,
            amount_at_risk=Decimal("250.00"),
            amount_recovered=Decimal("0.00"),
            status="open",
            current_attempt=1,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        # --------------------------------------------------
        # 2. First partial payment: ₹100
        # --------------------------------------------------

        first_event = NormalizedEvent(
            event_id=f"evt_partial_1_{uuid.uuid4().hex}",
            source="razorpay",
            event_type="invoice_partially_paid",
            customer_id=case.customer_id,
            payment_id=None,
            order_id=None,
            subscription_id=None,
            invoice_id=invoice_id,
            amount=Decimal("250.00"),
            amount_paid=Decimal("100.00"),
            amount_due=Decimal("150.00"),
            currency="INR",
            status="partially_paid",
        )

        db.add(first_event)
        db.commit()

        record_invoice_partial_payment(
            normalized=first_event,
            db=db,
        )

        db.refresh(case)

        assert case.amount_recovered == Decimal("100.00")
        assert case.status == "open"

        # --------------------------------------------------
        # 3. Duplicate webhook: still cumulative ₹100
        # --------------------------------------------------

        duplicate_event = NormalizedEvent(
            event_id=f"evt_partial_duplicate_{uuid.uuid4().hex}",
            source="razorpay",
            event_type="invoice_partially_paid",
            customer_id=case.customer_id,
            payment_id=None,
            order_id=None,
            subscription_id=None,
            invoice_id=invoice_id,
            amount=Decimal("250.00"),
            amount_paid=Decimal("100.00"),
            amount_due=Decimal("150.00"),
            currency="INR",
            status="partially_paid",
        )

        db.add(duplicate_event)
        db.commit()

        record_invoice_partial_payment(
            normalized=duplicate_event,
            db=db,
        )

        db.refresh(case)

        assert case.amount_recovered == Decimal("100.00")
        assert case.status == "open"

        # --------------------------------------------------
        # 4. Second partial payment: cumulative ₹180
        # --------------------------------------------------

        second_event = NormalizedEvent(
            event_id=f"evt_partial_2_{uuid.uuid4().hex}",
            source="razorpay",
            event_type="invoice_partially_paid",
            customer_id=case.customer_id,
            payment_id=None,
            order_id=None,
            subscription_id=None,
            invoice_id=invoice_id,
            amount=Decimal("250.00"),
            amount_paid=Decimal("180.00"),
            amount_due=Decimal("70.00"),
            currency="INR",
            status="partially_paid",
        )

        db.add(second_event)
        db.commit()

        record_invoice_partial_payment(
            normalized=second_event,
            db=db,
        )

        db.refresh(case)

        assert case.amount_recovered == Decimal("180.00")
        assert case.status == "open"

        # --------------------------------------------------
        # 5. Final payment: cumulative ₹250
        # --------------------------------------------------

        final_event = NormalizedEvent(
            event_id=f"evt_partial_final_{uuid.uuid4().hex}",
            source="razorpay",
            event_type="invoice_partially_paid",
            customer_id=case.customer_id,
            payment_id=None,
            order_id=None,
            subscription_id=None,
            invoice_id=invoice_id,
            amount=Decimal("250.00"),
            amount_paid=Decimal("250.00"),
            amount_due=Decimal("0.00"),
            currency="INR",
            status="paid",
        )

        db.add(final_event)
        db.commit()

        record_invoice_partial_payment(
            normalized=final_event,
            db=db,
        )

        db.refresh(case)

        assert case.amount_recovered == Decimal("250.00")
        assert case.status == "recovered"
        assert case.resolved_at is not None

    finally:
        db.close()


def test_partial_payment_reconciles_from_raw_invoice_when_normalized_due_is_wrong():
    """A real invoice partial event must not become recovered because due=0 was normalized incorrectly."""
    from app.db.models import Event

    db = SessionLocal()
    invoice_id = f"inv_raw_reconcile_{uuid.uuid4().hex}"
    event_id = f"evt_raw_reconcile_{uuid.uuid4().hex}"
    customer_id = f"cust_raw_reconcile_{uuid.uuid4().hex}"

    try:
        db.add(
            Event(
                source="razorpay",
                event_id=event_id,
                event_type="invoice.partially_paid",
                payload={
                    "event": "invoice.partially_paid",
                    "payload": {
                        "payment": {
                            "entity": {
                                "id": "pay_partial_raw",
                                "amount": 10000000,
                                "currency": "INR",
                                "status": "captured",
                            }
                        },
                        "invoice": {
                            "entity": {
                                "id": invoice_id,
                                "customer_id": customer_id,
                                "amount": 35700000,
                                "amount_paid": 10000000,
                                "amount_due": 25700000,
                                "currency": "INR",
                                "status": "partially_paid",
                            }
                        },
                    },
                },
            )
        )
        normalized = NormalizedEvent(
            event_id=event_id,
            source="razorpay",
            event_type="invoice_partially_paid",
            customer_id=customer_id,
            payment_id="pay_partial_raw",
            order_id=None,
            subscription_id=None,
            invoice_id=invoice_id,
            # Simulate the bad normalized values observed in production.
            amount=Decimal("357000.00"),
            amount_paid=Decimal("0.00"),
            amount_due=Decimal("0.00"),
            currency="INR",
            status="partially_paid",
        )
        db.add(normalized)
        db.commit()

        case = record_invoice_partial_payment(normalized=normalized, db=db)
        db.refresh(case)

        assert case.amount_at_risk == Decimal("357000.00")
        assert case.amount_recovered == Decimal("100000.00")
        assert case.amount_at_risk - case.amount_recovered == Decimal("257000.00")
        assert case.status == "open"
        assert case.resolved_at is None
    finally:
        db.close()
