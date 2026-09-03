from decimal import Decimal

from app.state.context import RecoveryContext
from app.state.guardrail import validate_recovery_decision
from app.state.recovery import RecoveryDecision


def make_context(
    *,
    previous_attempts=0,
    previous_recovery_attempts=None,
):
    return RecoveryContext(
        event_id="evt_guardrail_test",
        event_type="payment_failed",
        payment_id="pay_guardrail_test",
        order_id="order_guardrail_test",
        amount=Decimal("499.00"),
        currency="INR",
        payment_status="failed",
        customer_id="cust_guardrail_test",
        previous_attempts=previous_attempts,
        previous_recovery_attempts=previous_recovery_attempts or [],
    )


def make_decision(action, channel, confidence=0.90):
    return RecoveryDecision(
        action=action,
        channel=channel,
        reason="Test decision.",
        message="Test message.",
        confidence=confidence,
        priority="medium",
    )


def test_valid_decision():
    context = make_context()

    approved, reason = validate_recovery_decision(
        context,
        make_decision("send_payment_link", "email"),
    )

    assert approved is True
    assert reason == "Decision approved for execution."


def test_no_action_requires_none_channel():
    context = make_context()

    approved, reason = validate_recovery_decision(
        context,
        make_decision("no_action", "whatsapp"),
    )

    assert approved is False


def test_recovery_action_requires_channel():
    context = make_context()

    approved, reason = validate_recovery_decision(
        context,
        make_decision("send_payment_link", "none"),
    )

    assert approved is False


def test_contact_support_requires_none_channel():
    context = make_context()

    approved, reason = validate_recovery_decision(
        context,
        make_decision("contact_support", "none"),
    )

    assert approved is True


def test_attempt_limit_rejects_automated_recovery():
    context = make_context(previous_attempts=3)

    approved, reason = validate_recovery_decision(
        context,
        make_decision("send_payment_link", "email"),
    )

    assert approved is False
    assert "Recovery attempt limit reached" in reason


def test_already_escalated_case_rejects_duplicate_support():
    context = make_context(
        previous_attempts=4,
        previous_recovery_attempts=[
            {
                "id": 1,
                "action": "send_payment_link",
                "channel": "email",
                "status": "sent",
            },
            {
                "id": 2,
                "action": "send_payment_link",
                "channel": "sms",
                "status": "failed",
            },
            {
                "id": 3,
                "action": "send_payment_link",
                "channel": "whatsapp",
                "status": "blocked",
            },
            {
                "id": 4,
                "action": "contact_support",
                "channel": "none",
                "status": "escalated",
            },
        ],
    )

    approved, reason = validate_recovery_decision(
        context,
        make_decision("contact_support", "none"),
    )

    assert approved is False
    assert "already escalated to support" in reason


def test_no_action_allowed_after_support_escalation():
    context = make_context(
        previous_attempts=4,
        previous_recovery_attempts=[
            {
                "id": 4,
                "action": "contact_support",
                "channel": "none",
                "status": "escalated",
            }
        ],
    )

    approved, reason = validate_recovery_decision(
        context,
        make_decision("no_action", "none"),
    )

    assert approved is True
    assert reason == "Decision approved: no action required."
def test_attempt_limit_blocks_normal_recovery_after_three_attempts():
    context = make_context(
        previous_attempts=3,
    )
    decision = make_decision(
        action="send_payment_link",
        channel="email",
    )

    approved, reason = validate_recovery_decision(
        context,
        decision,
    )

    assert approved is False
    assert reason == (
        "Recovery attempt limit reached. "
        "Only contact_support or no_action is allowed."
    )


def test_attempt_limit_allows_contact_support():
    context = make_context(
        previous_attempts=3,
    )
    decision = make_decision(
        action="contact_support",
        channel="none",
    )

    approved, reason = validate_recovery_decision(
        context,
        decision,
    )

    assert approved is True
    assert reason == (
        "Decision approved: support escalation required."
    )


def test_attempt_limit_allows_no_action():
    context = make_context(
        previous_attempts=3,
    )
    decision = make_decision(
        action="no_action",
        channel="none",
    )

    approved, reason = validate_recovery_decision(
        context,
        decision,
    )

    assert approved is True
    assert reason == (
        "Decision approved: no action required."
    )


def test_payment_link_whatsapp_is_rejected_when_real_execution_is_unsupported():
    context = make_context()

    decision = make_decision(
        action="send_payment_link",
        channel="whatsapp",
    )

    approved, reason = validate_recovery_decision(
        context,
        decision,
    )

    assert approved is False
    assert reason == (
        "Recovery action/channel combination is not "
        "currently supported for real execution. "
        "Payment Link execution currently supports email and sms only."
    )
