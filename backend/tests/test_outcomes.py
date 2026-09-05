from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.state.outcomes import mark_recovery_succeeded


def test_mark_recovery_succeeded_updates_attempt_and_case():
    attempt = SimpleNamespace(
        id=999,
        status="sent",
        case_id="case_test_001",
        order_id="order_test_001",
        payment_id="pay_test_001",
        amount_at_risk=Decimal("500.00"),
        amount_recovered=None,
        resolved_at=None,
        subscription_id=None,
        invoice_id=None,
    )

    case = SimpleNamespace(
        id="case_test_001",
    )

    db = MagicMock()

    with (
        patch(
            "app.state.outcomes.get_recovery_case",
            return_value=case,
        ) as get_case,
        patch(
            "app.state.outcomes.mark_case_recovered",
        ) as mark_case,
    ):
        result = mark_recovery_succeeded(
            attempt=attempt,
            db=db,
            amount_recovered=Decimal("499.00"),
        )

    assert result is attempt
    assert attempt.status == "succeeded"
    assert attempt.amount_recovered == Decimal("499.00")
    assert attempt.resolved_at is not None

    get_case.assert_called_once_with(
        db,
        case_id="case_test_001",
        order_id="order_test_001",
        payment_id="pay_test_001",
        subscription_id=None,
        invoice_id=None,
    )

    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(attempt)

    mark_case.assert_called_once_with(
        db,
        case,
        payment_id="pay_test_001",
        amount_recovered=Decimal("499.00"),
    )

def test_duplicate_success_does_not_change_succeeded_attempt():
    attempt = SimpleNamespace(
        id=1000,
        status="succeeded",
        case_id="case_test_002",
        order_id="order_test_002",
        payment_id="pay_test_002",
        amount_at_risk=Decimal("800.00"),
        amount_recovered=Decimal("800.00"),
        resolved_at=MagicMock(),
    )

    db = MagicMock()

    result = mark_recovery_succeeded(
        attempt=attempt,
        db=db,
        amount_recovered=Decimal("800.00"),
    )

    assert result is attempt
    assert attempt.status == "succeeded"
    assert attempt.amount_recovered == Decimal("800.00")

    db.commit.assert_not_called()
    db.refresh.assert_not_called()
