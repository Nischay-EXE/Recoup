from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.recovery_models import (
    RecoveryAttempt,
    RecoveryCase,
    RecoveryDecisionRecord,
    RecoveryEscalation,
    RecoveryEscalationNote,
)
from app.state.case_service import mark_case_escalated


TEAM_BY_REVENUE_OBJECT = {
    "payment": "payments",
    "subscription": "customer_success",
    "invoice": "accounts_receivable",
}


def _get_assigned_team(case: RecoveryCase) -> str:
    revenue_object_type = getattr(case, "revenue_object_type", None)

    return TEAM_BY_REVENUE_OBJECT.get(
        revenue_object_type,
        "revenue_operations",
    )


def _build_summary(
    case: RecoveryCase,
    reason_code: str,
) -> str:
    amount_at_risk = case.amount_at_risk or 0
    amount_recovered = case.amount_recovered or 0
    remaining = amount_at_risk - amount_recovered

    return (
        f"Recovery case {case.case_id} was escalated because "
        f"{reason_code.replace('_', ' ')}. "
        f"Amount at risk: {amount_at_risk}. "
        f"Amount recovered: {amount_recovered}. "
        f"Remaining exposure: {remaining}."
    )


def _build_diagnosis(
    case: RecoveryCase,
    attempts: list[RecoveryAttempt],
) -> str:
    if not attempts:
        return (
            "The case has no recorded recovery attempts. "
            "Automated recovery could not establish a viable recovery path."
        )

    attempt_details = []

    for attempt in attempts:
        detail = (
            f"Attempt #{attempt.attempt_number}: "
            f"{attempt.action} via {attempt.channel}, "
            f"status={attempt.status}"
        )

        if attempt.execution_error:
            detail += f", execution error={attempt.execution_error}"

        if attempt.policy_reason:
            detail += f", policy={attempt.policy_reason}"

        attempt_details.append(detail)

    return "Recovery history: " + "; ".join(attempt_details) + "."


def _build_recommended_action(
    case: RecoveryCase,
    attempts: list[RecoveryAttempt],
) -> str:
    revenue_object_type = getattr(case, "revenue_object_type", None)

    if revenue_object_type == "invoice":
        return (
            "Contact the customer's accounts-payable or finance contact. "
            "Confirm invoice receipt, outstanding balance, payment status, "
            "and expected payment date."
        )

    if revenue_object_type == "subscription":
        return (
            "Contact the customer to determine why the subscription charge "
            "could not be completed and help them restore a valid payment method."
        )

    if revenue_object_type == "payment":
        return (
            "Contact the customer and verify the payment issue. "
            "Offer an appropriate supported payment method or payment link "
            "through the normal support workflow."
        )

    return (
        "Review the recovery history and contact the customer to determine "
        "the appropriate manual recovery action."
    )


def create_support_escalation(
    db: Session,
    case: RecoveryCase,
    reason_code: str,
) -> RecoveryEscalation:
    """
    Create an idempotent, support-ready escalation package.

    Escalation itself remains deterministic. This service packages the
    existing recovery history for human support.
    """

    existing = db.scalar(
        select(RecoveryEscalation).where(
            RecoveryEscalation.case_id == case.case_id
        )
    )

    if existing is not None:
        return existing

    attempts = list(
        db.scalars(
            select(RecoveryAttempt)
            .where(RecoveryAttempt.case_id == case.case_id)
            .order_by(
                RecoveryAttempt.attempt_number.asc(),
                RecoveryAttempt.created_at.asc(),
            )
        )
    )

    # Ensure the RecoveryCase is terminal before handing it to support.
    mark_case_escalated(db, case)

    escalation = RecoveryEscalation(
        case_id=case.case_id,
        batch_id=getattr(case, "batch_id", None),
        reason_code=reason_code,
        summary=_build_summary(case, reason_code),
        diagnosis=_build_diagnosis(case, attempts),
        recommended_action=_build_recommended_action(case, attempts),
        priority="high",
        assigned_team=_get_assigned_team(case),
        assigned_to=None,
        status="open",
    )

    db.add(escalation)
    db.commit()
    db.refresh(escalation)

    return escalation

def assign_support_escalation(
    db: Session,
    case_id: str,
    assigned_team: str | None = None,
    assigned_to: str | None = None,
) -> RecoveryEscalation | None:
    escalation = db.scalar(
        select(RecoveryEscalation).where(
            RecoveryEscalation.case_id == case_id
        )
    )

    if escalation is None:
        return None

    if escalation.status == "resolved":
        raise ValueError("Cannot assign a resolved escalation")

    if assigned_team is not None:
        escalation.assigned_team = assigned_team

    if assigned_to is not None:
        escalation.assigned_to = assigned_to

    db.commit()
    db.refresh(escalation)

    return escalation


def add_support_escalation_note(
    db: Session,
    case_id: str,
    note: str,
    created_by: str | None = None,
) -> RecoveryEscalationNote | None:
    escalation = db.scalar(
        select(RecoveryEscalation).where(
            RecoveryEscalation.case_id == case_id
        )
    )

    if escalation is None:
        return None

    if escalation.status == "resolved":
        raise ValueError("Cannot add a note to a resolved escalation")

    escalation_note = RecoveryEscalationNote(
        case_id=case_id,
        note=note,
        created_by=created_by,
    )

    db.add(escalation_note)
    db.commit()
    db.refresh(escalation_note)

    return escalation_note

def resolve_support_escalation(
    db: Session,
    case_id: str,
) -> RecoveryEscalation | None:
    escalation = db.scalar(
        select(RecoveryEscalation).where(
            RecoveryEscalation.case_id == case_id
        )
    )

    if escalation is None:
        return None

    if escalation.status == "resolved":
        return escalation

    escalation.status = "resolved"
    escalation.resolved_at = datetime.utcnow()

    db.commit()
    db.refresh(escalation)

    return escalation
