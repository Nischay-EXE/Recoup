from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.database import SessionLocal
from app.state.events import get_recovery_event_detail, get_recovery_events
from app.state.escalation_query import get_support_escalation
from app.state.audit import get_recovery_case_timeline
from app.state.escalation_service import (
    add_support_escalation_note,
    assign_support_escalation,
    resolve_support_escalation,
)
from app.state.metrics import (
    get_recovery_breakdowns,
    get_recovery_metrics,
)
from app.state.cases import get_recovery_cases

router = APIRouter(
    prefix="/recovery",
    tags=["recovery"],
)


class EscalationAssignmentRequest(BaseModel):
    assigned_team: str | None = None
    assigned_to: str | None = None

class EscalationNoteRequest(BaseModel):
    note: str
    created_by: str | None = None

@router.get("/metrics")
def recovery_metrics():
    db = SessionLocal()

    try:
        return get_recovery_metrics(db)
    finally:
        db.close()


@router.get("/metrics/breakdowns")
def recovery_metric_breakdowns():
    db = SessionLocal()

    try:
        return get_recovery_breakdowns(db)
    finally:
        db.close()
@router.get("/cases")
def recovery_cases(
    status: str | None = None,
    revenue_object_type: str | None = None,
    batch_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=422,
            detail="limit must be between 1 and 100",
        )

    if offset < 0:
        raise HTTPException(
            status_code=422,
            detail="offset must be greater than or equal to 0",
        )

    db = SessionLocal()

    try:
        return get_recovery_cases(
            db=db,
            status=status,
            revenue_object_type=revenue_object_type,
            batch_id=batch_id,
            limit=limit,
            offset=offset,
        )
    finally:
        db.close()

@router.get("/cases/{case_id}/timeline")
def recovery_case_timeline(case_id: str):
    db = SessionLocal()

    try:
        try:
            return get_recovery_case_timeline(
                case_id,
                db,
            )
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=f"Recovery case not found: {case_id}",
            )
    finally:
        db.close()


@router.get("/cases/{case_id}/escalation")
def recovery_case_escalation(case_id: str):
    db = SessionLocal()

    try:
        escalation = get_support_escalation(
            db=db,
            case_id=case_id,
        )

        if escalation is None:
            raise HTTPException(
                status_code=404,
                detail=f"Recovery escalation not found: {case_id}",
            )

        return escalation
    finally:
        db.close()


@router.patch("/cases/{case_id}/escalation/assignment")
def assign_recovery_case_escalation(
    case_id: str,
    request: EscalationAssignmentRequest,
):
    db = SessionLocal()

    try:
        try:
            escalation = assign_support_escalation(
                db=db,
                case_id=case_id,
                assigned_team=request.assigned_team,
                assigned_to=request.assigned_to,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            )

        if escalation is None:
            raise HTTPException(
                status_code=404,
                detail=f"Recovery escalation not found: {case_id}",
            )

        return get_support_escalation(
            db=db,
            case_id=case_id,
        )
    finally:
        db.close()

@router.post("/cases/{case_id}/escalation/notes")
def add_recovery_case_escalation_note(
    case_id: str,
    request: EscalationNoteRequest,
):
    db = SessionLocal()

    try:
        if not request.note.strip():
            raise HTTPException(
                status_code=422,
                detail="Note cannot be empty",
            )

        try:
            escalation_note = add_support_escalation_note(
                db=db,
                case_id=case_id,
                note=request.note.strip(),
                created_by=request.created_by,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            )

        if escalation_note is None:
            raise HTTPException(
                status_code=404,
                detail=f"Recovery escalation not found: {case_id}",
            )

        return {
            "id": escalation_note.id,
            "case_id": escalation_note.case_id,
            "note": escalation_note.note,
            "created_by": escalation_note.created_by,
            "created_at": escalation_note.created_at,
        }
    finally:
        db.close()

@router.post("/cases/{case_id}/escalation/resolve")
def resolve_recovery_case_escalation(case_id: str):
    db = SessionLocal()

    try:
        escalation = resolve_support_escalation(
            db=db,
            case_id=case_id,
        )

        if escalation is None:
            raise HTTPException(
                status_code=404,
                detail=f"Recovery escalation not found: {case_id}",
            )

        return get_support_escalation(
            db=db,
            case_id=case_id,
        )
    finally:
        db.close()

@router.get("/events")
def recovery_events(
    search: str | None = None,
    event_type: str | None = None,
    revenue_object_type: str | None = None,
    batch_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 100",
        )

    if offset < 0:
        raise HTTPException(
            status_code=400,
            detail="offset must be >= 0",
        )

    db = SessionLocal()

    try:
        return get_recovery_events(
            db=db,
            search=search,
            event_type=event_type,
            revenue_object_type=revenue_object_type,
            batch_id=batch_id,
            limit=limit,
            offset=offset,
        )
    finally:
        db.close()


@router.get("/events/{event_id}")
def recovery_event_detail(event_id: str):
    db = SessionLocal()
    try:
        event = get_recovery_event_detail(db=db, event_id=event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Recovery event not found: {event_id}")
        return event
    finally:
        db.close()
