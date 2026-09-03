from types import SimpleNamespace
from unittest.mock import MagicMock

from app.state.correlation import find_recovery_attempt


def test_correlation_prefers_exact_recovery_attempt_id():
    db = MagicMock()

    attempt = SimpleNamespace(
        id=70,
        status="sent",
        attempt_number=1,
    )

    (
        db.query.return_value
        .filter.return_value
        .first.return_value
    ) = attempt

    result = find_recovery_attempt(
        db,
        recovery_attempt_id=70,
        payment_id="pay_other",
        order_id="order_other",
    )

    assert result is attempt


def test_correlation_uses_payment_id_when_no_explicit_lineage():
    db = MagicMock()

    attempt = SimpleNamespace(
        id=71,
        status="sent",
        payment_id="pay_123",
        attempt_number=1,
    )

    (
        db.query.return_value
        .filter.return_value
        .order_by.return_value
        .first.return_value
    ) = attempt

    result = find_recovery_attempt(
        db,
        payment_id="pay_123",
    )

    assert result is attempt


def test_case_correlation_returns_only_candidate():
    db = MagicMock()

    attempt = SimpleNamespace(
        id=72,
        status="sent",
        case_id="case_123",
        attempt_number=1,
    )

    (
        db.query.return_value
        .filter.return_value
        .order_by.return_value
        .all.return_value
    ) = [attempt]

    result = find_recovery_attempt(
        db,
        recovery_case_id="case_123",
    )

    assert result is attempt


def test_case_correlation_does_not_guess_between_multiple_attempts():
    db = MagicMock()

    attempt_1 = SimpleNamespace(
        id=73,
        status="succeeded",
        case_id="case_456",
        attempt_number=1,
    )

    attempt_2 = SimpleNamespace(
        id=74,
        status="succeeded",
        case_id="case_456",
        attempt_number=2,
    )

    (
        db.query.return_value
        .filter.return_value
        .order_by.return_value
        .all.return_value
    ) = [attempt_2, attempt_1]

    result = find_recovery_attempt(
        db,
        recovery_case_id="case_456",
    )

    assert result is None


def test_customer_fallback_requires_exactly_one_active_attempt():
    db = MagicMock()

    attempt = SimpleNamespace(
        id=75,
        status="sent",
        customer_id="cust_123",
        attempt_number=1,
    )

    (
        db.query.return_value
        .filter.return_value
        .order_by.return_value
        .all.return_value
    ) = [attempt]

    result = find_recovery_attempt(
        db,
        customer_id="cust_123",
    )

    assert result is attempt


def test_customer_fallback_does_not_guess_multiple_active_attempts():
    db = MagicMock()

    attempt_1 = SimpleNamespace(
        id=76,
        status="sent",
        customer_id="cust_789",
        attempt_number=1,
    )

    attempt_2 = SimpleNamespace(
        id=77,
        status="sent",
        customer_id="cust_789",
        attempt_number=2,
    )

    (
        db.query.return_value
        .filter.return_value
        .order_by.return_value
        .all.return_value
    ) = [attempt_2, attempt_1]

    result = find_recovery_attempt(
        db,
        customer_id="cust_789",
    )

    assert result is None