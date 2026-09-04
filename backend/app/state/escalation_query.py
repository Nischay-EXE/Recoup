from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.recovery_models import RecoveryCase, RecoveryEscalation


def get_support_escalation(
    db: Session,
    case_id: str,
) -> dict | None:
    escalation = db.scalar(
        select(RecoveryEscalation).where(
            RecoveryEscalation.case_id == case_id
        )
    )

    if escalation is None:
        return None

    case = db.scalar(
        select(RecoveryCase).where(
            RecoveryCase.case_id == case_id
        )
    )

    if case is None:
        return None

    amount_at_risk = case.amount_at_risk or 0
    amount_recovered = case.amount_recovered or 0

    return {
        "case_id": case.case_id,
        "status": escalation.status,
        "reason_code": escalation.reason_code,
        "priority": escalation.priority,
        "assigned_team": escalation.assigned_team,
        "assigned_to": escalation.assigned_to,
        "summary": escalation.summary,
        "diagnosis": escalation.diagnosis,
        "recommended_action": escalation.recommended_action,
        "amount_at_risk": amount_at_risk,
        "amount_recovered": amount_recovered,
        "amount_remaining": amount_at_risk - amount_recovered,
        "created_at": escalation.created_at,
        "resolved_at": escalation.resolved_at,
    }