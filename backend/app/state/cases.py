from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.recovery_models import RecoveryCase


def get_recovery_cases(
    db: Session,
    *,
    status: str | None = None,
    revenue_object_type: str | None = None,
    batch_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """
    Return a read-only, paginated list of recovery cases.

    This function does not modify recovery state or history.
    """

    query = db.query(RecoveryCase)

    if status:
        query = query.filter(
            RecoveryCase.status == status
        )

    if revenue_object_type:
        query = query.filter(
            RecoveryCase.revenue_object_type
            == revenue_object_type
        )

    if batch_id:
        query = query.filter(RecoveryCase.batch_id == batch_id)

    total = query.with_entities(
        func.count(RecoveryCase.id)
    ).scalar() or 0

    cases = (
        query
        .order_by(
            RecoveryCase.created_at.desc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []

    for case in cases:
        amount_at_risk = (
            case.amount_at_risk
            or Decimal("0.00")
        )

        amount_recovered = (
            case.amount_recovered
            or Decimal("0.00")
        )

        items.append(
            {
                "case_id": case.case_id,
                "batch_id": case.batch_id,
                "customer_id": case.customer_id,
                "order_id": case.order_id,
                "revenue_object_type": (
                    case.revenue_object_type
                ),
                "subscription_id": case.subscription_id,
                "invoice_id": case.invoice_id,
                "original_payment_id": (
                    case.original_payment_id
                ),
                "current_payment_id": (
                    case.current_payment_id
                ),
                "amount_at_risk": amount_at_risk,
                "amount_recovered": amount_recovered,
                "amount_remaining": (
                    amount_at_risk
                    - amount_recovered
                ),
                "status": case.status,
                "current_attempt": (
                    case.current_attempt
                ),
                "created_at": case.created_at,
                "resolved_at": case.resolved_at,
            }
        )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }
