from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.recovery_models import RecoveryAttempt, RecoveryCase


TERMINAL_CASE_STATUSES = {
    "recovered",
    "resolved",
    "closed",
    "escalated",
}


def get_recovery_metrics(db: Session) -> dict:
    """
    Return aggregate recovery metrics from persisted RecoveryCase
    and RecoveryAttempt records.

    This is read-only. It does not modify recovery state or history.
    """

    total_cases = (
        db.query(func.count(RecoveryCase.id))
        .scalar()
        or 0
    )

    recovered_cases = (
        db.query(func.count(RecoveryCase.id))
        .filter(RecoveryCase.status == "recovered")
        .scalar()
        or 0
    )

    escalated_cases = (
        db.query(func.count(RecoveryCase.id))
        .filter(RecoveryCase.status == "escalated")
        .scalar()
        or 0
    )

    unresolved_cases = (
        db.query(func.count(RecoveryCase.id))
        .filter(~RecoveryCase.status.in_(TERMINAL_CASE_STATUSES))
        .scalar()
        or 0
    )

    amount_at_risk = (
        db.query(func.coalesce(func.sum(RecoveryCase.amount_at_risk), 0))
        .scalar()
        or Decimal("0")
    )

    amount_recovered = (
        db.query(func.coalesce(func.sum(RecoveryCase.amount_recovered), 0))
        .scalar()
        or Decimal("0")
    )

    total_attempts = (
        db.query(func.count(RecoveryAttempt.id))
        .scalar()
        or 0
    )

    recovery_rate = (
        (Decimal(amount_recovered) / Decimal(amount_at_risk)) * Decimal("100")
        if amount_at_risk
        else Decimal("0")
    )

    return {
        "total_cases": total_cases,
        "recovered_cases": recovered_cases,
        "escalated_cases": escalated_cases,
        "unresolved_cases": unresolved_cases,
        "amount_at_risk": amount_at_risk,
        "amount_recovered": amount_recovered,
        "total_attempts": total_attempts,
        "recovery_rate": recovery_rate.quantize(Decimal("0.01")),
    }


def get_recovery_breakdowns(db: Session) -> dict:
    """
    Return read-only recovery performance breakdowns.

    Revenue-object type is sourced from RecoveryCase.
    Action/channel/outcome data is sourced from RecoveryAttempt.
    """

    rows = (
        db.query(
            RecoveryAttempt,
            RecoveryCase.revenue_object_type,
        )
        .outerjoin(
            RecoveryCase,
            RecoveryAttempt.case_id == RecoveryCase.case_id,
        )
        .all()
    )

    by_revenue_object = defaultdict(
        lambda: {
            "attempts": 0,
            "recovered_attempts": 0,
            "amount_recovered": Decimal("0"),
        }
    )

    by_action = defaultdict(
        lambda: {
            "attempts": 0,
            "recovered_attempts": 0,
            "amount_recovered": Decimal("0"),
        }
    )

    by_channel = defaultdict(
        lambda: {
            "attempts": 0,
            "recovered_attempts": 0,
            "amount_recovered": Decimal("0"),
        }
    )

    for attempt, revenue_object_type in rows:
        amount_recovered = (
            attempt.amount_recovered
            or Decimal("0")
        )

        revenue_object = (
            revenue_object_type
            or "unknown"
        )

        action = attempt.action or "unknown"
        channel = attempt.channel or "unknown"

        is_recovered = (
            attempt.status == "succeeded"
            and amount_recovered > Decimal("0")
        )

        # ---------------------------------------------
        # Revenue object breakdown
        # ---------------------------------------------

        by_revenue_object[revenue_object]["attempts"] += 1

        if is_recovered:
            by_revenue_object[revenue_object][
                "recovered_attempts"
            ] += 1

        by_revenue_object[revenue_object][
            "amount_recovered"
        ] += amount_recovered

        # ---------------------------------------------
        # Action breakdown
        # ---------------------------------------------

        by_action[action]["attempts"] += 1

        if is_recovered:
            by_action[action]["recovered_attempts"] += 1

        by_action[action]["amount_recovered"] += (
            amount_recovered
        )

        # ---------------------------------------------
        # Channel breakdown
        # ---------------------------------------------

        by_channel[channel]["attempts"] += 1

        if is_recovered:
            by_channel[channel]["recovered_attempts"] += 1

        by_channel[channel]["amount_recovered"] += (
            amount_recovered
        )

    def serialize_breakdown(data: dict) -> dict:
        return {
            key: {
                "attempts": value["attempts"],
                "recovered_attempts": value[
                    "recovered_attempts"
                ],
                "amount_recovered": value[
                    "amount_recovered"
                ],
            }
            for key, value in data.items()
        }

    return {
        "by_revenue_object": serialize_breakdown(
            by_revenue_object
        ),
        "by_action": serialize_breakdown(
            by_action
        ),
        "by_channel": serialize_breakdown(
            by_channel
        ),
    }