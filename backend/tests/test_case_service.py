from decimal import Decimal
from unittest.mock import MagicMock

from app.db.recovery_models import RecoveryCase
from app.state.case_service import (
    create_recovery_case,
    get_recovery_case,
    get_or_create_recovery_case,
    increment_attempt,
    mark_case_escalated,
    mark_case_recovered,
    register_payment_attempt,
)


def make_db():
    return MagicMock()


def make_case(
    *,
    status="open",
    current_attempt=0,
    amount_recovered=Decimal("0.00"),
    amount_at_risk=Decimal("100.00"),
):
    return RecoveryCase(
        case_id="case_test",
        customer_id="cust_test",
        order_id="order_test",
        original_payment_id="pay_original",
        current_payment_id="pay_original",
        amount_at_risk=amount_at_risk,
        amount_recovered=amount_recovered,
        status=status,
        current_attempt=current_attempt,
        revenue_object_type="payment",
    )


# ==========================================================
# mark_case_escalated
# ==========================================================


def test_mark_case_escalated_changes_open_case_to_escalated():
    db = make_db()
    case = make_case(status="open")

    result = mark_case_escalated(db, case)

    assert result.status == "escalated"
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(case)


def test_mark_case_escalated_is_idempotent():
    db = make_db()
    case = make_case(status="escalated")

    result = mark_case_escalated(db, case)

    assert result.status == "escalated"

    # Already escalated, so no database write is required.
    db.commit.assert_not_called()
    db.refresh.assert_not_called()


def test_mark_case_escalated_does_not_change_recovered_case():
    db = make_db()
    case = make_case(status="recovered")

    result = mark_case_escalated(db, case)

    assert result.status == "recovered"
    db.commit.assert_not_called()
    db.refresh.assert_not_called()


def test_mark_case_escalated_does_not_change_resolved_case():
    db = make_db()
    case = make_case(status="resolved")

    result = mark_case_escalated(db, case)

    assert result.status == "resolved"
    db.commit.assert_not_called()
    db.refresh.assert_not_called()


def test_mark_case_escalated_does_not_change_closed_case():
    db = make_db()
    case = make_case(status="closed")

    result = mark_case_escalated(db, case)

    assert result.status == "closed"
    db.commit.assert_not_called()
    db.refresh.assert_not_called()


# ==========================================================
# Existing case lifecycle behavior
# ==========================================================


def test_increment_attempt():
    db = make_db()
    case = make_case(current_attempt=1)

    result = increment_attempt(db, case)

    assert result.current_attempt == 2
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(case)


def test_register_payment_attempt():
    db = make_db()
    case = make_case()

    result = register_payment_attempt(
        db,
        case,
        payment_id="pay_retry",
    )

    assert result.current_payment_id == "pay_retry"
    assert result.original_payment_id == "pay_original"

    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(case)


def test_mark_case_recovered():
    db = make_db()
    case = make_case()

    result = mark_case_recovered(
        db,
        case,
        payment_id="pay_retry",
        amount_recovered=Decimal("100.00"),
    )

    assert result.status == "recovered"
    assert result.current_payment_id == "pay_retry"
    assert result.amount_recovered == Decimal("100.00")
    assert result.resolved_at is not None

    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(case)
