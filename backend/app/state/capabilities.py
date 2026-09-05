from typing import Final


# ==========================================================
# Recovery execution capabilities
# ==========================================================

EXECUTION_CAPABILITIES: Final = {
    "retry_payment": {
        "channels": ["email", "sms"],
    },
    "send_payment_link": {
        "channels": ["email", "sms"],
    },
    "send_reminder": {
        "channels": ["email", "sms"],
    },
    "contact_support": {
        "channels": ["none"],
    },
    "no_action": {
        "channels": ["none"],
    },
}


def get_execution_capabilities() -> dict:
    """
    Return the recovery actions and channels that the
    current Executor implementation can actually execute.

    This is the single source of truth for execution
    capabilities used by the Strategist, Guardrail, and Executor.
    """

    return {
        action: {
            "channels": list(config["channels"]),
        }
        for action, config in EXECUTION_CAPABILITIES.items()
    }


def is_supported_action(action: str) -> bool:
    """Return whether the action is executable."""

    return action in EXECUTION_CAPABILITIES


def is_supported_combination(
    action: str,
    channel: str,
) -> bool:
    """Return whether an action/channel combination is executable."""

    capability = EXECUTION_CAPABILITIES.get(action)

    if capability is None:
        return False

    return channel in capability["channels"]
