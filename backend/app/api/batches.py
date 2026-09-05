from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.database import SessionLocal
from app.state.batch_service import create_batch, close_batch, delete_batch, get_batch, list_batches, reopen_batch

router = APIRouter(prefix="/recovery/batches", tags=["recovery-batches"])


class BatchCreateRequest(BaseModel):
    name: str
    description: str | None = None


@router.get("")
def recovery_batches(limit: int = 20, offset: int = 0):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    if offset < 0:
        raise HTTPException(status_code=422, detail="offset must be greater than or equal to 0")
    db = SessionLocal()
    try:
        return list_batches(db, limit=limit, offset=offset)
    finally:
        db.close()


@router.get("/{batch_id}")
def recovery_batch(batch_id: str):
    db = SessionLocal()
    try:
        batch = get_batch(db, batch_id)
        if batch is None:
            raise HTTPException(status_code=404, detail=f"Recovery batch not found: {batch_id}")
        return batch
    finally:
        db.close()


@router.post("")
def start_recovery_batch(request: BatchCreateRequest):
    if not request.name.strip():
        raise HTTPException(status_code=422, detail="Batch name cannot be empty")
    db = SessionLocal()
    try:
        try:
            batch = create_batch(db, name=request.name, description=request.description)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        return get_batch(db, batch.batch_id)
    finally:
        db.close()


@router.post("/{batch_id}/close")
def finish_recovery_batch(batch_id: str):
    db = SessionLocal()
    try:
        batch = close_batch(db, batch_id)
        if batch is None:
            raise HTTPException(status_code=404, detail=f"Recovery batch not found: {batch_id}")
        return get_batch(db, batch_id)
    finally:
        db.close()


@router.post("/{batch_id}/open")
def reopen_recovery_batch(batch_id: str):
    db = SessionLocal()
    try:
        try:
            batch = reopen_batch(db, batch_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        if batch is None:
            raise HTTPException(status_code=404, detail=f"Recovery batch not found: {batch_id}")
        return get_batch(db, batch_id)
    finally:
        db.close()


@router.delete("/{batch_id}")
def remove_recovery_batch(batch_id: str):
    db = SessionLocal()
    try:
        try:
            batch = delete_batch(db, batch_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        if batch is None:
            raise HTTPException(status_code=404, detail=f"Recovery batch not found: {batch_id}")
        return {
            "status": "deleted",
            "batch_id": batch.batch_id,
        }
    finally:
        db.close()
