from decimal import Decimal
from app.normalization.razorpay import normalize_razorpay_event


def test_normalize_subscription_pending_event():
    payload = {
        "event": "subscription.pending",
        "created_at": 1700000000,
        "payload": {
            "subscription": {
                "entity": {
                    "id": "sub_123",
                    "customer_id": "cust_123",
                    "status": "pending",
                    "created_at": 1700000000,
                }
            }
        },
    }

    result = normalize_razorpay_event(
        payload=payload,
        event_id="evt_subscription_pending",
    )

    assert result.event_type == "subscription_pending"
    assert result.subscription_id == "sub_123"
    assert result.customer_id == "cust_123"
    assert result.status == "pending"
    assert result.payment_id is None
    assert result.invoice_id is None


def test_normalize_subscription_halted_event():
    payload = {
        "event": "subscription.halted",
        "created_at": 1700000000,
        "payload": {
            "subscription": {
                "entity": {
                    "id": "sub_456",
                    "customer_id": "cust_456",
                    "status": "halted",
                    "created_at": 1700000000,
                }
            }
        },
    }

    result = normalize_razorpay_event(
        payload=payload,
        event_id="evt_subscription_halted",
    )

    assert result.event_type == "subscription_halted"
    assert result.subscription_id == "sub_456"
    assert result.customer_id == "cust_456"
    assert result.status == "halted"
    assert result.payment_id is None
    assert result.invoice_id is None


def test_normalize_subscription_charged_event():
    payload = {
        "event": "subscription.charged",
        "created_at": 1700000000,
        "payload": {
            "subscription": {
                "entity": {
                    "id": "sub_789",
                    "customer_id": "cust_789",
                    "status": "active",
                    "created_at": 1700000000,
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_789",
                    "customer_id": "cust_789",
                    "subscription_id": "sub_789",
                    "invoice_id": "inv_789",
                    "amount": 150000,
                    "currency": "INR",
                    "status": "captured",
                    "created_at": 1700000000,
                }
            },
            "invoice": {
                "entity": {
                    "id": "inv_789",
                    "customer_id": "cust_789",
                    "amount": 150000,
                    "currency": "INR",
                    "status": "paid",
                    "created_at": 1700000000,
                }
            },
        },
    }

    result = normalize_razorpay_event(
        payload=payload,
        event_id="evt_subscription_charged",
    )

    assert result.event_type == "subscription_charged"
    assert result.subscription_id == "sub_789"
    assert result.payment_id == "pay_789"
    assert result.invoice_id == "inv_789"
    assert result.customer_id == "cust_789"
    assert result.amount == 1500
    assert result.currency == "INR"
    assert result.status == "captured"


def test_normalize_invoice_partial_payment_uses_invoice_total_not_payment_amount():
    """Invoice amount is the full invoice even when a nested payment is partial."""
    payload = {
        "entity": "event",
        "event": "invoice.partially_paid",
        "contains": ["payment", "order", "invoice"],
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_partial_100000",
                    "amount": 10000000,
                    "currency": "INR",
                    "status": "attempted",
                    "order_id": "order_partial_001",
                }
            },
            "invoice": {
                "entity": {
                    "id": "inv_partial_001",
                    "customer_id": "cust_partial_001",
                    "order_id": "order_partial_001",
                    "payment_id": "pay_partial_100000",
                    "status": "partially_paid",
                    "amount": 44600000,
                    "amount_paid": 10000000,
                    "amount_due": 34600000,
                    "currency": "INR",
                }
            },
        },
    }

    result = normalize_razorpay_event(
        payload=payload,
        event_id="evt_invoice_partial_001",
    )

    assert result.event_type == "invoice_partially_paid"
    assert result.invoice_id == "inv_partial_001"
    assert result.payment_id == "pay_partial_100000"
    assert result.amount == Decimal("446000.00")
    assert result.amount_paid == Decimal("100000.00")
    assert result.amount_due == Decimal("346000.00")
    assert result.status == "partially_paid"
