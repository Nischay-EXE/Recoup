import uuid
from decimal import Decimal
from sqlalchemy.orm import Session
from unittest.mock import MagicMock
from types import SimpleNamespace

from app.db.database import SessionLocal
from app.db.recovery_models import RecoveryAttempt, RecoveryDecisionRecord
from app.state.correlation import find_recovery_attempt
from app.state.case_service import get_or_create_recovery_case
def test_subscription_charged_correlates_when_exactly_one_attempt_exists():
    db = SessionLocal()

    try:
        subscription_id = f"sub_single_candidate_{uuid.uuid4().hex}"
        customer_id = f"cust_single_candidate_{uuid.uuid4().hex}"

        case = get_or_create_recovery_case(
            db,
            customer_id=customer_id,
            order_id=None,
            payment_id=None,
            amount=Decimal("999.00"),
            revenue_object_type="subscription",
            subscription_id=subscription_id,
            invoice_id=None,
        )

        attempt = RecoveryAttempt(
            event_id=f"evt_single_candidate_{uuid.uuid4().hex}",
            case_id=case.case_id,
            payment_id=None,
            order_id=None,
            subscription_id=subscription_id,
            invoice_id=None,
            customer_id=customer_id,
            action="send_payment_link",
            channel="email",
            ai_reason="Subscription requires recovery",
            ai_confidence=0.90,
            policy_result="approved",
            policy_reason="Allowed",
            attempt_number=1,
            status="sent",
            amount_at_risk=Decimal("999.00"),
            amount_recovered=Decimal("0.00"),
        )

        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        # The charged outcome contains only the subscription identity.
        result = find_recovery_attempt(
            db,
            subscription_id=subscription_id,
        )

        assert result is not None
        assert result.id == attempt.id
        assert result.subscription_id == subscription_id
        assert result.status == "sent"

    finally:
        db.close()
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

def test_correlation_uses_subscription_id_when_no_payment_match():
    db = MagicMock()

    attempt = SimpleNamespace(
        id=78,
        status="sent",
        subscription_id="sub_123",
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
        subscription_id="sub_123",
    )

    assert result is attempt


def test_correlation_uses_invoice_id_when_no_payment_or_subscription_match():
    db = MagicMock()

    attempt = SimpleNamespace(
        id=79,
        status="sent",
        invoice_id="inv_123",
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
        invoice_id="inv_123",
    )

    assert result is attempt


def test_correlation_prefers_payment_id_over_subscription_id():
    db = MagicMock()

    payment_attempt = SimpleNamespace(
        id=80,
        status="sent",
        payment_id="pay_123",
        attempt_number=2,
    )

    (
        db.query.return_value
        .filter.return_value
        .order_by.return_value
        .first.return_value
    ) = payment_attempt

    result = find_recovery_attempt(
        db,
        payment_id="pay_123",
        subscription_id="sub_123",
    )

    assert result is payment_attempt