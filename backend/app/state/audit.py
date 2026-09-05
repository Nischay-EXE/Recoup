from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.recovery_models import (
    RecoveryAttempt,
    RecoveryCase,
    RecoveryDecisionRecord,
    RecoveryEscalation,
)


def _event(
    *,
    timestamp: datetime | None,
    event_type: str,
    description: str,
    **details: Any,
) -> dict:
    return {
        "timestamp": timestamp,
        "event_type": event_type,
        "description": description,
        "details": details,
    }


def get_recovery_case_timeline(
    case_id: str,
    db: Session,
) -> dict:
    """
    Return a chronological, read-only audit timeline for one
    RecoveryCase.

    The timeline is derived from existing RecoveryCase,
    RecoveryDecisionRecord, RecoveryAttempt, and
    RecoveryEscalation records.

    No audit state is created or modified.
    """

    case = (
        db.query(RecoveryCase)
        .filter(
            RecoveryCase.case_id == case_id
        )
        .first()
    )

    if case is None:
        raise ValueError(
            f"Recovery case not found: {case_id}"
        )

    attempts = (
        db.query(RecoveryAttempt)
        .filter(
            RecoveryAttempt.case_id == case.case_id
        )
        .order_by(
            RecoveryAttempt.attempt_number.asc()
        )
        .all()
    )

    event_ids = {
        attempt.event_id
        for attempt in attempts
        if attempt.event_id
    }

    decisions = []

    if event_ids:
        decisions = (
            db.query(RecoveryDecisionRecord)
            .filter(
                RecoveryDecisionRecord.event_id.in_(event_ids)
            )
            .all()
        )

    decisions_by_event = {
        decision.event_id: decision
        for decision in decisions
    }

    escalation = (
        db.query(RecoveryEscalation)
        .filter(
            RecoveryEscalation.case_id == case.case_id
        )
        .first()
    )

    timeline: list[dict] = []

    # --------------------------------------------------
    # Case creation
    # --------------------------------------------------

    timeline.append(
        _event(
            timestamp=case.created_at,
            event_type="case_created",
            description="Recovery case created",
            case_id=case.case_id,
            revenue_object_type=case.revenue_object_type,
            amount_at_risk=case.amount_at_risk,
        )
    )

    # --------------------------------------------------
    # Recovery decisions + attempts
    # --------------------------------------------------

    for attempt in attempts:
        decision = decisions_by_event.get(
            attempt.event_id
        )

        if decision is not None:
            decision_source = (
                "deterministic_escalation"
                if decision.action == "contact_support"
                else "recovery_decision"
            )

            timeline.append(
                _event(
                    timestamp=decision.created_at,
                    event_type="decision_created",
                    description="Recovery strategy decided",
                    decision_id=decision.id,
                    event_id=decision.event_id,
                    decision_source=decision_source,
                    action=decision.action,
                    channel=decision.channel,
                    reason=decision.reason,
                    message=decision.message,
                    confidence=decision.confidence,
                    priority=decision.priority,
                )
            )

        # --------------------------------------------------
        # Guardrail evaluation
        # --------------------------------------------------

        if (
            attempt.policy_result is not None
            or attempt.policy_reason is not None
        ):
            timeline.append(
                _event(
                    timestamp=attempt.created_at,
                    event_type="guardrail_evaluated",
                    description="Recovery policy evaluated",
                    attempt_id=attempt.id,
                    attempt_number=attempt.attempt_number,
                    policy_result=attempt.policy_result,
                    policy_reason=attempt.policy_reason,
                    action=attempt.action,
                    channel=attempt.channel,
                )
            )

        # --------------------------------------------------
        # Attempt creation
        # --------------------------------------------------

        timeline.append(
            _event(
                timestamp=attempt.created_at,
                event_type="attempt_created",
                description="Recovery attempt created",
                attempt_id=attempt.id,
                attempt_number=attempt.attempt_number,
                event_id=attempt.event_id,
                action=attempt.action,
                channel=attempt.channel,
                status=attempt.status,
            )
        )

        # --------------------------------------------------
        # Attempt scheduling
        # --------------------------------------------------

        if attempt.scheduled_at is not None:
            timeline.append(
                _event(
                    timestamp=attempt.scheduled_at,
                    event_type="attempt_scheduled",
                    description="Recovery attempt scheduled",
                    attempt_id=attempt.id,
                    attempt_number=attempt.attempt_number,
                    scheduled_at=attempt.scheduled_at,
                )
            )

        # --------------------------------------------------
        # Attempt execution
        # --------------------------------------------------

        if attempt.executed_at is not None:
            timeline.append(
                _event(
                    timestamp=attempt.executed_at,
                    event_type="attempt_executed",
                    description="Recovery attempt executed",
                    attempt_id=attempt.id,
                    attempt_number=attempt.attempt_number,
                    action=attempt.action,
                    channel=attempt.channel,
                    status=attempt.status,
                    execution_provider=attempt.execution_provider,
                    external_execution_id=attempt.external_execution_id,
                    external_execution_url=attempt.external_execution_url,
                    execution_error=attempt.execution_error,
                )
            )

        # --------------------------------------------------
        # Attempt resolution
        # --------------------------------------------------

        if attempt.resolved_at is not None:
            timeline.append(
                _event(
                    timestamp=attempt.resolved_at,
                    event_type="attempt_resolved",
                    description="Recovery attempt resolved",
                    attempt_id=attempt.id,
                    attempt_number=attempt.attempt_number,
                    status=attempt.status,
                    amount_recovered=attempt.amount_recovered,
                    execution_error=attempt.execution_error,
                )
            )

    # --------------------------------------------------
    # Escalation
    # --------------------------------------------------

    if escalation is not None:
        timeline.append(
            _event(
                timestamp=escalation.created_at,
                event_type="escalation_created",
                description="Recovery case escalated to support",
                escalation_id=escalation.id,
                case_id=escalation.case_id,
                reason_code=escalation.reason_code,
                summary=escalation.summary,
                diagnosis=escalation.diagnosis,
                recommended_action=escalation.recommended_action,
                priority=escalation.priority,
                assigned_team=escalation.assigned_team,
                assigned_to=escalation.assigned_to,
                status=escalation.status,
                resolved_at=escalation.resolved_at,
            )
        )

    # --------------------------------------------------
    # Case resolution
    # --------------------------------------------------

    if case.resolved_at is not None:
        timeline.append(
            _event(
                timestamp=case.resolved_at,
                event_type="case_resolved",
                description="Recovery case resolved",
                case_id=case.case_id,
                status=case.status,
                amount_recovered=case.amount_recovered,
            )
        )

    # --------------------------------------------------
    # Chronological ordering
    # --------------------------------------------------

    timeline.sort(
        key=lambda item: (
            item["timestamp"] is None,
            item["timestamp"],
        )
    )

    return {
        "case_id": case.case_id,
        "customer_id": case.customer_id,
        "revenue_object_type": case.revenue_object_type,
        "amount_at_risk": case.amount_at_risk,
        "amount_recovered": case.amount_recovered,
        "status": case.status,
        "timeline": timeline,
    }
