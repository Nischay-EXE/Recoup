from decimal import Decimal

from app.state.escalation import evaluate_escalation_rules


def test_terminal_case_does_not_escalate():
    decision = evaluate_escalation_rules(
        case_status="recovered",
        attempt_count=3,
        amount_recovered=Decimal("100.00"),
        amount_at_risk=Decimal("100.00"),
        failed_attempts=5,
    )

    assert decision.should_escalate is False
    assert decision.reason == "case_terminal"


def test_resolved_payment_does_not_escalate():
    decision = evaluate_escalation_rules(
        case_status="open",
        attempt_count=3,
        amount_recovered=Decimal("0.00"),
        amount_at_risk=Decimal("100.00"),
        payment_status="captured",
        failed_attempts=5,
    )

    assert decision.should_escalate is False
    assert decision.reason == "payment_resolved"


def test_fully_recovered_case_does_not_escalate():
    decision = evaluate_escalation_rules(
        case_status="open",
        attempt_count=2,
        amount_recovered=Decimal("100.00"),
        amount_at_risk=Decimal("100.00"),
        failed_attempts=5,
    )

    assert decision.should_escalate is False
    assert decision.reason == "amount_fully_recovered"


def test_repeated_failures_escalate():
    decision = evaluate_escalation_rules(
        case_status="open",
        attempt_count=2,
        amount_recovered=Decimal("0.00"),
        amount_at_risk=Decimal("100.00"),
        failed_attempts=3,
    )

    assert decision.should_escalate is True
    assert decision.reason == "repeated_recovery_failures"


def test_no_viable_recovery_path_escalates():
    decision = evaluate_escalation_rules(
        case_status="open",
        attempt_count=1,
        amount_recovered=Decimal("0.00"),
        amount_at_risk=Decimal("100.00"),
        has_viable_recovery_path=False,
    )

    assert decision.should_escalate is True
    assert decision.reason == "no_viable_recovery_path"


def test_attempt_boundary_escalates():
    decision = evaluate_escalation_rules(
        case_status="open",
        attempt_count=3,
        amount_recovered=Decimal("0.00"),
        amount_at_risk=Decimal("100.00"),
    )

    assert decision.should_escalate is True
    assert decision.reason == "recovery_exhausted"


def test_recovery_can_continue():
    decision = evaluate_escalation_rules(
        case_status="open",
        attempt_count=1,
        amount_recovered=Decimal("0.00"),
        amount_at_risk=Decimal("100.00"),
        failed_attempts=1,
    )

    assert decision.should_escalate is False
    assert decision.reason == "recovery_can_continue"


def test_partial_recovery_can_continue():
    decision = evaluate_escalation_rules(
        case_status="open",
        attempt_count=2,
        amount_recovered=Decimal("40.00"),
        amount_at_risk=Decimal("100.00"),
        failed_attempts=1,
    )

    assert decision.should_escalate is False
    assert decision.reason == "recovery_can_continue"