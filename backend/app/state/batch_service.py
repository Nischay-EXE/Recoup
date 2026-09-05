from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.batch_models import RecoveryBatch
from app.db.models import Event
from app.db.normalized_models import NormalizedEvent
from app.db.recovery_models import RecoveryAttempt, RecoveryCase, RecoveryEscalation
from app.utils.time import utc_now


def get_active_batch(db: Session) -> RecoveryBatch | None:
    return (
        db.query(RecoveryBatch)
        .filter(RecoveryBatch.status == "active")
        .order_by(RecoveryBatch.started_at.desc())
        .first()
    )


def create_batch(db: Session, *, name: str, description: str | None = None) -> RecoveryBatch:
    if get_active_batch(db) is not None:
        raise ValueError("An active recovery batch already exists. Close it before starting another batch.")

    now = utc_now()
    batch = RecoveryBatch(
        batch_id=f"batch_{uuid4().hex}",
        name=name.strip(),
        description=description.strip() if description else None,
        status="active",
        started_at=now,
        created_at=now,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def close_batch(db: Session, batch_id: str) -> RecoveryBatch | None:
    batch = db.query(RecoveryBatch).filter(RecoveryBatch.batch_id == batch_id).first()
    if batch is None:
        return None
    if batch.status == "active":
        batch.status = "completed"
        batch.ended_at = utc_now()
        db.commit()
        db.refresh(batch)
    return batch


def reopen_batch(db: Session, batch_id: str) -> RecoveryBatch | None:
    """Re-enable a completed batch as the current active assignment boundary."""
    batch = db.query(RecoveryBatch).filter(RecoveryBatch.batch_id == batch_id).first()
    if batch is None or batch.status == "deleted":
        return None

    active = get_active_batch(db)
    if active is not None and active.batch_id != batch_id:
        raise ValueError(
            "Another active recovery batch already exists. Disable it before enabling this batch."
        )

    batch.status = "active"
    batch.ended_at = None
    db.commit()
    db.refresh(batch)
    return batch


def delete_batch(db: Session, batch_id: str) -> RecoveryBatch | None:
    """Soft-delete a batch boundary without deleting its audit records."""
    batch = db.query(RecoveryBatch).filter(RecoveryBatch.batch_id == batch_id).first()
    if batch is None or batch.status == "deleted":
        return None
    if batch.status == "active":
        raise ValueError("Disable the active recovery batch before deleting it.")

    # Never delete Event/Case/Attempt/Decision/Escalation rows.  The batch
    # remains in the database as an audit tombstone and is simply hidden from
    # the operational batch list.
    if batch.status == "active":
        batch.ended_at = utc_now()
    batch.status = "deleted"
    db.commit()
    db.refresh(batch)
    return batch


def _serialize_batch(db: Session, batch: RecoveryBatch) -> dict:
    event_count = db.query(func.count(Event.id)).filter(Event.batch_id == batch.batch_id).scalar() or 0
    normalized_event_count = db.query(func.count(NormalizedEvent.id)).filter(NormalizedEvent.batch_id == batch.batch_id).scalar() or 0
    payment_count = (
        db.query(func.count(func.distinct(NormalizedEvent.payment_id)))
        .filter(NormalizedEvent.batch_id == batch.batch_id, NormalizedEvent.payment_id.isnot(None))
        .scalar() or 0
    )
    case_count = db.query(func.count(RecoveryCase.id)).filter(RecoveryCase.batch_id == batch.batch_id).scalar() or 0
    attempt_count = db.query(func.count(RecoveryAttempt.id)).filter(RecoveryAttempt.batch_id == batch.batch_id).scalar() or 0
    escalated_count = db.query(func.count(RecoveryEscalation.id)).filter(RecoveryEscalation.batch_id == batch.batch_id).scalar() or 0
    amount_at_risk = db.query(func.coalesce(func.sum(RecoveryCase.amount_at_risk), 0)).filter(RecoveryCase.batch_id == batch.batch_id).scalar() or Decimal("0")
    amount_recovered = db.query(func.coalesce(func.sum(RecoveryCase.amount_recovered), 0)).filter(RecoveryCase.batch_id == batch.batch_id).scalar() or Decimal("0")
    recovery_rate = (Decimal(amount_recovered) / Decimal(amount_at_risk) * Decimal("100")) if amount_at_risk else Decimal("0")

    return {
        "batch_id": batch.batch_id,
        "name": batch.name,
        "description": batch.description,
        "status": batch.status,
        "started_at": batch.started_at,
        "ended_at": batch.ended_at,
        "created_at": batch.created_at,
        "event_count": event_count,
        "normalized_event_count": normalized_event_count,
        "payment_count": payment_count,
        "case_count": case_count,
        "attempt_count": attempt_count,
        "escalated_count": escalated_count,
        "amount_at_risk": amount_at_risk,
        "amount_recovered": amount_recovered,
        "recovery_rate": recovery_rate.quantize(Decimal("0.01")),
    }


def list_batches(db: Session, *, limit: int = 20, offset: int = 0) -> dict:
    query = db.query(RecoveryBatch).filter(RecoveryBatch.status != "deleted")
    total = query.with_entities(func.count(RecoveryBatch.id)).scalar() or 0
    batches = query.order_by(RecoveryBatch.started_at.desc()).offset(offset).limit(limit).all()
    return {
        "items": [_serialize_batch(db, batch) for batch in batches],
        "total": total,
        "limit": limit,
        "offset": offset,
        "active_batch_id": (get_active_batch(db).batch_id if get_active_batch(db) else None),
    }


def get_batch(db: Session, batch_id: str) -> dict | None:
    batch = db.query(RecoveryBatch).filter(RecoveryBatch.batch_id == batch_id).first()
    if batch is None or batch.status == "deleted":
        return None
    return _serialize_batch(db, batch)
