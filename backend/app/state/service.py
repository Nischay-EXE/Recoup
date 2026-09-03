from sqlalchemy.orm import Session

from app.db.recovery_models import RecoveryDecisionRecord
from app.state.context import RecoveryContext

from app.agent.analyst_agent import analyze_recovery_context
from app.agent.strategist_agent import propose_strategy


def build_customer_message(action: str) -> str:
    """
    Build the customer-facing message from the approved recovery action.

    The Strategist decides WHAT to do.
    This function decides the basic customer-facing wording.
    """

    if action == "send_payment_link":
        return (
            "Your payment didn't go through. "
            "You can retry your payment using the secure payment link."
        )

    if action == "contact_support":
        return (
            "We noticed multiple unsuccessful payment attempts. "
            "Our support team can help you complete your payment."
        )

    if action == "send_reminder":
        return (
            "This is a reminder that your payment is still pending. "
            "Please complete your payment using the secure payment link."
        )

    if action == "retry_payment":
        return (
            "Your payment could not be completed. "
            "Please try your payment again."
        )

    if action == "no_action":
        return ""

    return ""


def create_recovery_decision(
    context: RecoveryContext,
    db: Session,
) -> RecoveryDecisionRecord:

    # --------------------------------------------------
    # 1. Check whether a decision already exists
    # --------------------------------------------------

    existing_decision = (
        db.query(RecoveryDecisionRecord)
        .filter(
            RecoveryDecisionRecord.event_id == context.event_id
        )
        .first()
    )

    if existing_decision:
        return existing_decision

    # --------------------------------------------------
    # 2. Agent 1 — Recovery Analyst
    # --------------------------------------------------

    analyst_report = analyze_recovery_context(context)

    # --------------------------------------------------
    # 3. Agent 2 — Recovery Strategist
    # --------------------------------------------------

    strategy = propose_strategy(
        context=context,
        analyst_report=analyst_report,
    )

    # --------------------------------------------------
    # 4. Build customer-facing message
    # --------------------------------------------------

    message = build_customer_message(
        strategy.action
    )

    # --------------------------------------------------
    # 5. Persist final decision
    # --------------------------------------------------

    record = RecoveryDecisionRecord(
        event_id=context.event_id,
        action=strategy.action,
        channel=strategy.channel,
        reason=strategy.reason,
        message=message,
        confidence=float(strategy.confidence),
        priority=strategy.priority,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record