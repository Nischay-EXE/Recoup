from app.state.context import RecoveryContext
from app.state.recovery import RecoveryDecision



def decide_recovery(context: RecoveryContext) -> RecoveryDecision:
    """
    Deterministic recovery policy.

    The policy decides what should happen based on
    the normalized recovery context.
    """

    # Successful payment → nothing to recover
    if context.payment_status in {"captured", "paid", "success"}:
        return RecoveryDecision(
            action="no_action",
            channel="none",
            reason="Payment was successful.",
            message="",
            confidence=1.0,
            priority="low",
        )

    # Unknown/non-failed events → don't take recovery action
    if context.event_type != "payment_failed":
        return RecoveryDecision(
            action="no_action",
            channel="none",
            reason="Event is not a payment failure.",
            message="",
            confidence=1.0,
            priority="low",
        )

    # Repeated payment failures → escalate
    if context.previous_attempts >= 3:
        return RecoveryDecision(
            action="contact_support",
            channel="whatsapp",
            reason="Multiple payment attempts have failed.",
            message=(
                "We noticed multiple unsuccessful payment attempts. "
                "Our support team can help you complete your payment."
            ),
            confidence=0.95,
            priority="high",
        )

    # First/early failure → provide another payment opportunity
    return RecoveryDecision(
        action="send_payment_link",
        channel="whatsapp",
        reason="Payment failed and the order may still be recoverable.",
        message=(
            "Your payment didn't go through. "
            "You can retry your payment using the secure payment link."
        ),
        confidence=0.94,
        priority="high",
    )
