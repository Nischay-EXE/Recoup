from decimal import Decimal

from app.state.stopping_rules import evaluate_stopping_rules


def test_recovered_case_stops():
    result = evaluate_stopping_rules(
        case_status="recovered",
        attempt_count=0,
        amount_recovered=Decimal("0"),
        amount_at_risk=Decimal("100"),
    )

    assert result.should_stop is True
    assert result.reason == "case_terminal"


def test_resolved_case_stops():
    result = evaluate_stopping_rules(
        case_status="resolved",
        attempt_count=0,
        amount_recovered=Decimal("0"),
        amount_at_risk=Decimal("100"),
    )

    assert result.should_stop is True
    assert result.reason == "case_terminal"


def test_closed_case_stops():
    result = evaluate_stopping_rules(
        case_status="closed",
        attempt_count=0,
        amount_recovered=Decimal("0"),
        amount_at_risk=Decimal("100"),
    )

    assert result.should_stop is True
    assert result.reason == "case_terminal"


def test_escalated_case_stops():
    result = evaluate_stopping_rules(
        case_status="escalated",
        attempt_count=1,
        amount_recovered=Decimal("0"),
        amount_at_risk=Decimal("100"),
    )

    assert result.should_stop is True
    assert result.reason == "case_terminal"


def test_successful_payment_stops():
    result = evaluate_stopping_rules(
        case_status="open",
        attempt_count=1,
        amount_recovered=Decimal("0"),
        amount_at_risk=Decimal("100"),
        payment_status="captured",
    )

    assert result.should_stop is True
    assert result.reason == "payment_resolved"


def test_paid_payment_stops():
    result = evaluate_stopping_rules(
        case_status="open",
        attempt_count=1,
        amount_recovered=Decimal("0"),
        amount_at_risk=Decimal("100"),
        payment_status="paid",
    )

    assert result.should_stop is True
    assert result.reason == "payment_resolved"


def test_full_amount_recovered_stops():
    result = evaluate_stopping_rules(
        case_status="open",
        attempt_count=1,
        amount_recovered=Decimal("100"),
        amount_at_risk=Decimal("100"),
    )

    assert result.should_stop is True
    assert result.reason == "amount_fully_recovered"


def test_partial_recovery_can_continue():
    result = evaluate_stopping_rules(
        case_status="open",
        attempt_count=1,
        amount_recovered=Decimal("40"),
        amount_at_risk=Decimal("100"),
    )

    assert result.should_stop is False
    assert result.reason == "recovery_can_continue"


def test_open_case_can_continue_regardless_of_attempt_count():
    result = evaluate_stopping_rules(
        case_status="open",
        attempt_count=100,
        amount_recovered=Decimal("0"),
        amount_at_risk=Decimal("100"),
    )

    assert result.should_stop is False
    assert result.reason == "recovery_can_continue"


def test_terminal_case_takes_priority():
    result = evaluate_stopping_rules(
        case_status="recovered",
        attempt_count=100,
        amount_recovered=Decimal("100"),
        amount_at_risk=Decimal("100"),
    )

    assert result.should_stop is True
    assert result.reason == "case_terminal"