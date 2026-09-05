from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.state.escalation_service import create_support_escalation


def make_case(
    *,
    revenue_object_type="payment",
    amount_at_risk=Decimal("1000.00"),
    amount_recovered=Decimal("0.00"),
):
    return SimpleNamespace(
        case_id="case_test_001",
        revenue_object_type=revenue_object_type,
        customer_id="cust_test_001",
        amount_at_risk=amount_at_risk,
        amount_recovered=amount_recovered,
        status="open",
    )


def make_attempt(
    *,
    attempt_number,
    action,
    channel,
    status,
    execution_error=None,
    policy_reason=None,
):
    return SimpleNamespace(
        attempt_number=attempt_number,
        action=action,
        channel=channel,
        status=status,
        execution_error=execution_error,
        policy_reason=policy_reason,
    )


def test_create_support_escalation_builds_support_package():
    db = MagicMock()
    db.scalar.return_value = None

    attempts = [
        make_attempt(
            attempt_number=1,
            action="send_payment_link",
            channel="email",
            status="failed",
        ),
        make_attempt(
            attempt_number=2,
            action="send_reminder",
            channel="sms",
            status="failed",
            execution_error="Provider timeout",
        ),
    ]

    db.scalars.return_value = attempts

    case = make_case(
        revenue_object_type="payment",
        amount_at_risk=Decimal("1000.00"),
        amount_recovered=Decimal("250.00"),
    )

    with patch(
        "app.state.escalation_service.mark_case_escalated"
    ) as mark_escalated:
        escalation = create_support_escalation(
            db=db,
            case=case,
            reason_code="repeated_recovery_failures",
        )

    mark_escalated.assert_called_once_with(db, case)

    assert escalation.case_id == "case_test_001"
    assert escalation.reason_code == "repeated_recovery_failures"
    assert escalation.priority == "high"
    assert escalation.status == "open"

    assert "repeated recovery failures" in escalation.summary
    assert "1000.00" in escalation.summary
    assert "250.00" in escalation.summary
    assert "750.00" in escalation.summary

    assert "Attempt #1" in escalation.diagnosis
    assert "Attempt #2" in escalation.diagnosis
    assert "send_payment_link" in escalation.diagnosis
    assert "send_reminder" in escalation.diagnosis
    assert "Provider timeout" in escalation.diagnosis

    assert "Contact the customer" in escalation.recommended_action
    assert escalation.assigned_team == "payments"

    db.add.assert_called_once_with(escalation)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(escalation)


def test_escalation_routes_by_revenue_object_type():
    for revenue_object_type, expected_team in [
        ("payment", "payments"),
        ("subscription", "customer_success"),
        ("invoice", "accounts_receivable"),
    ]:
        db = MagicMock()
        db.scalar.return_value = None
        db.scalars.return_value = []

        case = make_case(
            revenue_object_type=revenue_object_type,
        )

        with patch(
            "app.state.escalation_service.mark_case_escalated"
        ):
            escalation = create_support_escalation(
                db=db,
                case=case,
                reason_code="recovery_exhausted",
            )

        assert escalation.assigned_team == expected_team


def test_invoice_escalation_recommends_accounts_receivable_action():
    db = MagicMock()
    db.scalar.return_value = None

    attempts = [
        make_attempt(
            attempt_number=1,
            action="send_reminder",
            channel="email",
            status="failed",
        ),
        make_attempt(
            attempt_number=2,
            action="send_payment_link",
            channel="email",
            status="failed",
        ),
    ]

    db.scalars.return_value = attempts

    case = make_case(
        revenue_object_type="invoice",
        amount_at_risk=Decimal("45000.00"),
        amount_recovered=Decimal("12000.00"),
    )

    with patch(
        "app.state.escalation_service.mark_case_escalated"
    ):
        escalation = create_support_escalation(
            db=db,
            case=case,
            reason_code="recovery_exhausted",
        )

    assert escalation.assigned_team == "accounts_receivable"

    assert "accounts-payable" in escalation.recommended_action
    assert "outstanding balance" in escalation.recommended_action
    assert "payment status" in escalation.recommended_action


def test_create_support_escalation_is_idempotent():
    db = MagicMock()

    existing = SimpleNamespace(
        case_id="case_test_001",
        status="open",
    )

    db.scalar.return_value = existing

    case = make_case()

    with patch(
        "app.state.escalation_service.mark_case_escalated"
    ) as mark_escalated:
        result = create_support_escalation(
            db=db,
            case=case,
            reason_code="recovery_exhausted",
        )

    assert result is existing

    mark_escalated.assert_not_called()
    db.scalars.assert_not_called()
    db.add.assert_not_called()
    db.commit.assert_not_called()
    db.refresh.assert_not_called()
