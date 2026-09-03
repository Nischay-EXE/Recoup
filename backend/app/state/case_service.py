from app.utils.time import utc_now
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.recovery_models import RecoveryCase


def get_recovery_case(
    db: Session,
    *,
    case_id: str | None = None,
    order_id: str | None = None,
    payment_id: str | None = None,
) -> RecoveryCase | None:
    """
    Find an existing recovery case.

    Lookup priority:
    1. case_id (explicit recovery lineage)
    2. current payment_id
    3. original payment_id
    4. open case for order_id
    """

    if case_id:
        case = (
            db.query(RecoveryCase)
            .filter(RecoveryCase.case_id == case_id)
            .first()
        )

        if case:
            return case

    if payment_id:
        case = (
            db.query(RecoveryCase)
            .filter(
                RecoveryCase.current_payment_id == payment_id
            )
            .first()
        )

        if case:
            return case

        case = (
            db.query(RecoveryCase)
            .filter(
                RecoveryCase.original_payment_id == payment_id
            )
            .first()
        )

        if case:
            return case

    if order_id:
        case = (
            db.query(RecoveryCase)
            .filter(
                RecoveryCase.order_id == order_id,
                RecoveryCase.status == "open",
            )
            .first()
        )

        if case:
            return case

    return None


def create_recovery_case(
    db: Session,
    *,
    customer_id: str | None,
    order_id: str | None,
    payment_id: str | None,
    amount: Decimal | None,
) -> RecoveryCase:
    """
    Create a recovery case for an initial payment failure.
    """

    case = RecoveryCase(
        case_id=f"case_{uuid4().hex}",
        customer_id=customer_id,
        order_id=order_id,
        original_payment_id=payment_id,
        current_payment_id=payment_id,
        amount_at_risk=amount,
        amount_recovered=Decimal("0.00"),
        status="open",
        current_attempt=0,
        created_at=utc_now(),
    )

    db.add(case)
    db.commit()
    db.refresh(case)

    return case


def get_or_create_recovery_case(
    db: Session,
    *,
    customer_id: str | None,
    order_id: str | None,
    payment_id: str | None,
    amount: Decimal | None,
    case_id: str | None = None,
) -> RecoveryCase:

    existing_case = get_recovery_case(
        db,
        case_id=case_id,
        order_id=order_id,
        payment_id=payment_id,
    )

    if existing_case:
        return existing_case

    return create_recovery_case(
        db,
        customer_id=customer_id,
        order_id=order_id,
        payment_id=payment_id,
        amount=amount,
    )


def register_payment_attempt(
    db: Session,
    case: RecoveryCase,
    *,
    payment_id: str,
) -> RecoveryCase:
    """
    Associate a newly generated retry payment with the case.

    The original payment ID is never changed.
    """

    case.current_payment_id = payment_id

    db.commit()
    db.refresh(case)

    return case


def increment_attempt(
    db: Session,
    case: RecoveryCase,
) -> RecoveryCase:
    """
    Increment the recovery attempt counter.
    """

    case.current_attempt += 1

    db.commit()
    db.refresh(case)

    return case


def mark_case_recovered(
    db: Session,
    case: RecoveryCase,
    *,
    payment_id: str,
    amount_recovered: Decimal,
) -> RecoveryCase:
    """
    Mark the entire recovery case as recovered.
    """

    case.current_payment_id = payment_id
    case.amount_recovered = amount_recovered
    case.status = "recovered"
    case.resolved_at = utc_now()

    db.commit()
    db.refresh(case)

    return case
