from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class EscalationDecision:
    should_escalate: bool
    reason: str


def evaluate_escalation_rules(
    *,
    case_status: str | None,
    attempt_count: int,
    amount_recovered: Decimal | None,
    amount_at_risk: Decimal | None,
    payment_status: str | None = None,
    failed_attempts: int = 0,
    has_viable_recovery_path: bool = True,
) -> EscalationDecision:
    """
    Deterministic escalation policy.

    This policy decides whether a recovery case should be handed
    over to human support. It does not execute the escalation.
    """

    # --------------------------------------------------
    # 1. Terminal cases should never be escalated
    # --------------------------------------------------

    if case_status in {
        "recovered",
        "resolved",
        "closed",
    }:
        return EscalationDecision(
            should_escalate=False,
            reason="case_terminal",
        )

    # --------------------------------------------------
    # 2. Revenue object is already resolved
    # --------------------------------------------------

    if payment_status in {
        "captured",
        "paid",
        "success",
        "succeeded",
    }:
        return EscalationDecision(
            should_escalate=False,
            reason="payment_resolved",
        )

    # --------------------------------------------------
    # 3. Entire amount has already been recovered
    # --------------------------------------------------

    if (
        amount_recovered is not None
        and amount_at_risk is not None
        and amount_recovered >= amount_at_risk
    ):
        return EscalationDecision(
            should_escalate=False,
            reason="amount_fully_recovered",
        )

    # --------------------------------------------------
    # 4. Repeated recovery failures
    # --------------------------------------------------

    if failed_attempts >= 3:
        return EscalationDecision(
            should_escalate=True,
            reason="repeated_recovery_failures",
        )

    # --------------------------------------------------
    # 5. No viable recovery path
    # --------------------------------------------------

    if not has_viable_recovery_path:
        return EscalationDecision(
            should_escalate=True,
            reason="no_viable_recovery_path",
        )

    # --------------------------------------------------
    # 6. Recovery attempt boundary reached
    #
    # Guardrail remains responsible for authorizing
    # individual recovery actions. This rule only
    # determines whether human escalation is now needed.
    # --------------------------------------------------

    if attempt_count >= 3:
        return EscalationDecision(
            should_escalate=True,
            reason="recovery_exhausted",
        )

    # --------------------------------------------------
    # 7. Recovery can continue
    # --------------------------------------------------

    return EscalationDecision(
        should_escalate=False,
        reason="recovery_can_continue",
    )
