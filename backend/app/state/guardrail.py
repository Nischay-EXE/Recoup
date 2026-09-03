from app.state.capabilities import (
    get_execution_capabilities,
    is_supported_action,
    is_supported_combination,
)
from app.state.context import RecoveryContext
from app.state.recovery import RecoveryDecision


def validate_recovery_decision(
    context: RecoveryContext,
    decision: RecoveryDecision,
) -> tuple[bool, str]:
    """
    Validate an AI-generated recovery decision before execution.

    Returns:
        (approved, reason)
    """

    # --------------------------------------------------
    # 1. Validate action
    # --------------------------------------------------

    if not is_supported_action(decision.action):
        return (
            False,
            f"Unsupported recovery action: {decision.action}",
        )

    # --------------------------------------------------
    # 2. Validate action/channel capability
    # --------------------------------------------------

    if not is_supported_combination(
        decision.action,
        decision.channel,
    ):
        capabilities = get_execution_capabilities()

        supported_channels = capabilities.get(
            decision.action,
            {},
        ).get("channels", [])

        if supported_channels:
            channels_text = ", ".join(supported_channels)

            return (
                    False,
                    "Recovery action/channel combination is not "
                    "currently supported for real execution. "
                    "Payment Link execution currently supports email and sms only.",
                )

        return (
            False,
            f"Unsupported recovery channel '{decision.channel}' "
            f"for action '{decision.action}'.",
        )

    # --------------------------------------------------
    # 3. Do not re-escalate an already escalated case
    # --------------------------------------------------

    support_already_escalated = any(
        attempt.get("action") == "contact_support"
        and attempt.get("status") == "escalated"
        for attempt in context.previous_recovery_attempts
    )

    if support_already_escalated and decision.action != "no_action":
        return (
            False,
            "Recovery case is already escalated to support. "
            "Only no_action is allowed.",
        )

    # --------------------------------------------------
    # 4. Prevent excessive recovery attempts
    # --------------------------------------------------

    if context.previous_attempts >= 3:
        if decision.action not in {
            "contact_support",
            "no_action",
        }:
            return (
                False,
                "Recovery attempt limit reached. "
                "Only contact_support or no_action is allowed.",
            )

    # --------------------------------------------------
    # 5. no_action must use none channel
    # --------------------------------------------------

    if decision.action == "no_action":
        if decision.channel != "none":
            return (
                False,
                "no_action decisions must use channel='none'.",
            )

        return True, "Decision approved: no action required."

    # --------------------------------------------------
    # 6. contact_support is an internal escalation
    # --------------------------------------------------

    if decision.action == "contact_support":
        if decision.channel != "none":
            return (
                False,
                "contact_support must use channel='none'.",
            )

        return True, "Decision approved: support escalation required."

    # --------------------------------------------------
    # 7. Other recovery actions require a real channel
    # --------------------------------------------------

    if decision.channel == "none":
        return (
            False,
            "Recovery actions require a communication channel.",
        )

    # --------------------------------------------------
    # 8. Only recover failed payments
    # --------------------------------------------------

    if context.payment_status in {
        "captured",
        "paid",
        "success",
    }:
        return (
            False,
            "Payment is already successful. Recovery action blocked.",
        )

    # --------------------------------------------------
    # 9. Only payment_failed events are recoverable
    # --------------------------------------------------

    if context.event_type != "payment_failed":
        return (
            False,
            "Event is not a payment failure. Recovery action blocked.",
        )

    return True, "Decision approved for execution."