from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class StoppingDecision:
    """
    Result of evaluating whether a recovery case should continue.

    Stopping rules are case-lifecycle rules.
    They do not authorize or reject a specific recovery action.
    """

    should_stop: bool
    reason: str


TERMINAL_CASE_STATUSES = {
    "recovered",
    "resolved",
    "closed",
    "escalated",
}


RESOLVED_PAYMENT_STATUSES = {
    "captured",
    "paid",
    "success",
    "succeeded",
}


def evaluate_stopping_rules(
    *,
    case_status: str | None,
    attempt_count: int,
    amount_recovered: Decimal | None,
    amount_at_risk: Decimal | None,
    payment_status: str | None = None,
) -> StoppingDecision:
    """
    Evaluate case-level stopping conditions.

    This function answers only:

        "Should this recovery case continue?"

    It does NOT answer:

        "Is a particular action/channel allowed?"

    That remains the responsibility of the deterministic guardrail.
    """

    # --------------------------------------------------
    # 1. Case is already terminal
    # --------------------------------------------------

    if case_status in TERMINAL_CASE_STATUSES:
        return StoppingDecision(
            should_stop=True,
            reason="case_terminal",
        )

    # --------------------------------------------------
    # 2. Payment is already resolved
    # --------------------------------------------------

    if payment_status in RESOLVED_PAYMENT_STATUSES:
        return StoppingDecision(
            should_stop=True,
            reason="payment_resolved",
        )

    # --------------------------------------------------
    # 3. Full amount has been recovered
    # --------------------------------------------------

    if (
        amount_recovered is not None
        and amount_at_risk is not None
        and amount_recovered >= amount_at_risk
    ):
        return StoppingDecision(
            should_stop=True,
            reason="amount_fully_recovered",
        )

    # --------------------------------------------------
    # 4. Case can continue
    #
    # Attempt/action limits intentionally do NOT live
    # here. The guardrail owns action-level attempt
    # authorization.
    # --------------------------------------------------

    return StoppingDecision(
        should_stop=False,
        reason="recovery_can_continue",
    )