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