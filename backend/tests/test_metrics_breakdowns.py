from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.state.metrics import get_recovery_breakdowns


def test_get_recovery_breakdowns_groups_attempts():
    db = MagicMock()

    payment_case = SimpleNamespace(
        revenue_object_type="payment",
    )

    invoice_case = SimpleNamespace(
        revenue_object_type="invoice",
    )

    payment_attempt_1 = SimpleNamespace(
        action="send_payment_link",
        channel="email",
        status="succeeded",
        amount_recovered=Decimal("500.00"),
    )

    payment_attempt_2 = SimpleNamespace(
        action="send_payment_link",
        channel="sms",
        status="failed",
        amount_recovered=Decimal("0"),
    )

    invoice_attempt = SimpleNamespace(
        action="send_reminder",
        channel="email",
        status="succeeded",
        amount_recovered=Decimal("250.00"),
    )

    rows = [
        (payment_attempt_1, payment_case.revenue_object_type),
        (payment_attempt_2, payment_case.revenue_object_type),
        (invoice_attempt, invoice_case.revenue_object_type),
    ]

    db.query.return_value.outerjoin.return_value.all.return_value = rows

    result = get_recovery_breakdowns(db)

    assert result["by_revenue_object"]["payment"]["attempts"] == 2
    assert result["by_revenue_object"]["payment"]["recovered_attempts"] == 1
    assert (
        result["by_revenue_object"]["payment"]["amount_recovered"]
        == Decimal("500.00")
    )

    assert result["by_revenue_object"]["invoice"]["attempts"] == 1
    assert result["by_revenue_object"]["invoice"]["recovered_attempts"] == 1
    assert (
        result["by_revenue_object"]["invoice"]["amount_recovered"]
        == Decimal("250.00")
    )

    assert result["by_action"]["send_payment_link"]["attempts"] == 2
    assert result["by_action"]["send_payment_link"]["recovered_attempts"] == 1

    assert result["by_action"]["send_reminder"]["attempts"] == 1
    assert result["by_action"]["send_reminder"]["recovered_attempts"] == 1

    assert result["by_channel"]["email"]["attempts"] == 2
    assert result["by_channel"]["email"]["recovered_attempts"] == 2

    assert result["by_channel"]["sms"]["attempts"] == 1
    assert result["by_channel"]["sms"]["recovered_attempts"] == 0

def test_get_recovery_breakdowns_does_not_create_unknown_for_orphan_payment_attempt():
    db = MagicMock()

    orphan_payment_attempt = SimpleNamespace(
        action="send_payment_link",
        channel="email",
        status="execution_failed",
        amount_recovered=Decimal("0"),
        payment_id="pay_orphan",
        order_id=None,
        subscription_id=None,
        invoice_id=None,
    )

    db.query.return_value.outerjoin.return_value.all.return_value = [
        (orphan_payment_attempt, None),
    ]

    result = get_recovery_breakdowns(db)

    assert "unknown" not in result["by_revenue_object"]
    assert result["by_revenue_object"]["payment"]["attempts"] == 1
