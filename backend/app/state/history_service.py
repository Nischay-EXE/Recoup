from app.utils.time import utc_now
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Any

from sqlalchemy.orm import Session

from app.db.history_models import Customer, Order, Payment


@dataclass
class HistorySyncResult:
    customer_id: str | None = None
    order_id: str | None = None
    payment_id: str | None = None


def _timestamp_to_datetime(
    timestamp: Any,
) -> datetime | None:
    if timestamp is None:
        return None

    try:
        return datetime.fromtimestamp(
            int(timestamp),
            tz=timezone.utc,
        ).replace(tzinfo=None)
    except (TypeError, ValueError, OverflowError):
        return None


def _amount_to_decimal(
    amount: Any,
) -> Decimal | None:
    if amount is None:
        return None

    try:
        return Decimal(str(amount)) / Decimal("100")
    except (TypeError, ValueError, ArithmeticError):
        return None


def _clean_email(
    email: Any,
) -> str | None:
    if not email:
        return None

    email = str(email).strip().lower()

    if not email:
        return None

    # Razorpay may expose this placeholder on some payment
    # entities. Do not use it as the real customer email.
    if email == "void@razorpay.com":
        return None

    return email


def _clean_phone(
    phone: Any,
) -> str | None:
    if not phone:
        return None

    phone = str(phone).strip()

    return phone or None


def _generate_customer_id(
    email: str | None,
    phone: str | None,
) -> str | None:
    parts = [
        value
        for value in (email, phone)
        if value
    ]

    if not parts:
        return None

    identity = "|".join(parts)

    digest = sha256(
        identity.encode("utf-8")
    ).hexdigest()[:24]

    return f"cust_{digest}"


def _extract_entities(
    payload: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    payload_data = payload.get(
        "payload",
        {},
    )

    if not isinstance(payload_data, dict):
        payload_data = {}

    order = payload_data.get(
        "order",
        {},
    )

    if not isinstance(order, dict):
        order = {}

    order_entity = order.get(
        "entity",
        {},
    )

    if not isinstance(order_entity, dict):
        order_entity = {}

    payment = payload_data.get(
        "payment",
        {},
    )

    if not isinstance(payment, dict):
        payment = {}

    payment_entity = payment.get(
        "entity",
        {},
    )

    if not isinstance(payment_entity, dict):
        payment_entity = {}

    payment_link = payload_data.get(
        "payment_link",
        {},
    )

    if not isinstance(payment_link, dict):
        payment_link = {}

    payment_link_entity = payment_link.get(
        "entity",
        {},
    )

    if not isinstance(payment_link_entity, dict):
        payment_link_entity = {}

    return (
        order_entity,
        payment_entity,
        payment_link_entity,
    )


def _extract_customer_data(
    order_entity: dict[str, Any],
    payment_entity: dict[str, Any],
    payment_link_entity: dict[str, Any],
) -> dict[str, Any]:
    """
    Collect customer information from the entities available
    in the Razorpay event.

    Priority:
        Payment Link customer
        Order customer
        Payment entity

    The Payment entity may expose void@razorpay.com, so that
    placeholder is ignored.
    """

    payment_link_customer = payment_link_entity.get(
        "customer",
        {},
    )

    if not isinstance(payment_link_customer, dict):
        payment_link_customer = {}

    order_customer = order_entity.get(
        "customer",
        {},
    )

    if not isinstance(order_customer, dict):
        order_customer = {}

    razorpay_customer_id = (
        payment_entity.get("customer_id")
        or order_entity.get("customer_id")
        or payment_link_entity.get("customer_id")
    )

    name = (
        payment_link_customer.get("name")
        or order_customer.get("name")
    )

    email = (
        _clean_email(
            payment_link_customer.get("email")
        )
        or _clean_email(
            order_customer.get("email")
        )
        or _clean_email(
            payment_entity.get("email")
        )
    )

    phone = (
        _clean_phone(
            payment_link_customer.get("contact")
        )
        or _clean_phone(
            order_customer.get("contact")
        )
        or _clean_phone(
            payment_entity.get("contact")
        )
    )

    return {
        "razorpay_customer_id": razorpay_customer_id,
        "name": name,
        "email": email,
        "phone": phone,
    }


def _find_customer_by_identity(
    db: Session,
    customer_data: dict[str, Any],
) -> Customer | None:
    """
    Find an existing customer using explicit identity fields.

    Priority:
        1. Razorpay customer_id
        2. email
        3. phone
    """

    razorpay_customer_id = (
        customer_data.get("razorpay_customer_id")
    )

    email = customer_data.get("email")
    phone = customer_data.get("phone")

    if razorpay_customer_id:
        customer = (
            db.query(Customer)
            .filter(
                Customer.customer_id
                == str(razorpay_customer_id)
            )
            .first()
        )

        if customer is not None:
            return customer

    if email:
        customer = (
            db.query(Customer)
            .filter(
                Customer.email == email
            )
            .first()
        )

        if customer is not None:
            return customer

    if phone and not email:
        customer = (
            db.query(Customer)
            .filter(
                Customer.phone == phone
            )
            .first()
        )

        if customer is not None:
            return customer

    return None


def _enrich_customer(
    customer: Customer,
    customer_data: dict[str, Any],
) -> Customer:
    """
    Add missing information to an existing customer.

    Never overwrite useful existing data with None.
    """

    name = customer_data.get("name")
    email = customer_data.get("email")
    phone = customer_data.get("phone")

    if customer.name is None and name:
        customer.name = name

    if customer.email is None and email:
        customer.email = email

    if customer.phone is None and phone:
        customer.phone = phone

    return customer


def _create_customer(
    db: Session,
    customer_data: dict[str, Any],
) -> Customer | None:
    """
    Create an internal customer only when we have enough
    information to establish an identity.
    """

    razorpay_customer_id = (
        customer_data.get("razorpay_customer_id")
    )

    email = customer_data.get("email")
    phone = customer_data.get("phone")
    name = customer_data.get("name")

    customer_id = (
        str(razorpay_customer_id)
        if razorpay_customer_id
        else _generate_customer_id(
            email=email,
            phone=phone,
        )
    )

    if customer_id is None:
        return None

    customer = Customer(
        customer_id=customer_id,
        name=name,
        email=email,
        phone=phone,
        created_at=utc_now(),
    )

    db.add(customer)
    db.flush()

    return customer


def _resolve_customer(
    db: Session,
    customer_data: dict[str, Any],
    existing_customer: Customer | None = None,
) -> Customer | None:
    """
    Resolve a customer.

    If the payment/order already provides a known customer,
    that relationship is preferred over creating a new one.
    """

    if existing_customer is not None:
        return _enrich_customer(
            existing_customer,
            customer_data,
        )

    customer = _find_customer_by_identity(
        db=db,
        customer_data=customer_data,
    )

    if customer is not None:
        return _enrich_customer(
            customer,
            customer_data,
        )

    return _create_customer(
        db=db,
        customer_data=customer_data,
    )


def sync_razorpay_history(
    payload: dict[str, Any],
    db: Session,
) -> HistorySyncResult:
    """
    Materialize useful Razorpay payment/order/customer data
    into the local history tables.

    Tables updated:
        customers
        orders
        payments

    The raw Razorpay event remains stored separately in
    Event.payload.

    This function does NOT commit. The webhook owns the
    transaction.
    """

    (
        order_entity,
        payment_entity,
        payment_link_entity,
    ) = _extract_entities(payload)

    customer_data = _extract_customer_data(
        order_entity=order_entity,
        payment_entity=payment_entity,
        payment_link_entity=payment_link_entity,
    )

    payment_id = payment_entity.get("id")

    order_id = (
        payment_entity.get("order_id")
        or order_entity.get("id")
        or payment_link_entity.get("order_id")
    )

    payment_id_str = (
        str(payment_id)
        if payment_id
        else None
    )

    order_id_str = (
        str(order_id)
        if order_id
        else None
    )

    # ==================================================
    # 1. Find existing PAYMENT
    # ==================================================

    existing_payment = None

    if payment_id_str:
        existing_payment = (
            db.query(Payment)
            .filter(
                Payment.payment_id
                == payment_id_str
            )
            .first()
        )

    # ==================================================
    # 2. Find existing ORDER
    # ==================================================

    existing_order = None

    if order_id_str:
        existing_order = (
            db.query(Order)
            .filter(
                Order.order_id
                == order_id_str
            )
            .first()
        )

    # ==================================================
    # 3. Resolve existing customer relationship
    #
    # This is the key deduplication step.
    #
    # Existing payment customer wins first.
    # Existing order customer wins second.
    # ==================================================

    known_customer_id = None

    if (
        existing_payment is not None
        and existing_payment.customer_id
    ):
        known_customer_id = (
            existing_payment.customer_id
        )

    elif (
        existing_order is not None
        and existing_order.customer_id
    ):
        known_customer_id = (
            existing_order.customer_id
        )

    existing_customer = None

    if known_customer_id:
        existing_customer = (
            db.query(Customer)
            .filter(
                Customer.customer_id
                == known_customer_id
            )
            .first()
        )

    # ==================================================
    # 4. Resolve customer
    # ==================================================

    customer = _resolve_customer(
        db=db,
        customer_data=customer_data,
        existing_customer=existing_customer,
    )

    customer_id = (
        customer.customer_id
        if customer is not None
        else None
    )

    # ==================================================
    # 5. If an existing order/payment had a customer_id
    # but the Customer record itself was missing, create
    # a local customer using that identity.
    # ==================================================

    if (
        customer is None
        and known_customer_id
    ):
        customer = Customer(
            customer_id=known_customer_id,
            name=customer_data.get("name"),
            email=customer_data.get("email"),
            phone=customer_data.get("phone"),
            created_at=utc_now(),
        )

        db.add(customer)
        db.flush()

        customer_id = customer.customer_id

    # ==================================================
    # 6. ORDER
    # ==================================================

    order_amount = (
        _amount_to_decimal(
            order_entity.get("amount")
        )
        or _amount_to_decimal(
            payment_entity.get("amount")
        )
        or _amount_to_decimal(
            payment_link_entity.get("amount")
        )
    )

    order_currency = (
        order_entity.get("currency")
        or payment_entity.get("currency")
        or payment_link_entity.get("currency")
    )

    order_status = order_entity.get(
        "status"
    )

    if existing_order is None and order_id_str:

        existing_order = Order(
            order_id=order_id_str,
            customer_id=customer_id,
            amount=order_amount,
            currency=order_currency,
            status=(
                str(order_status)
                if order_status
                else "created"
            ),
            created_at=(
                _timestamp_to_datetime(
                    order_entity.get("created_at")
                )
                or utc_now()
            ),
        )

        db.add(existing_order)

    elif existing_order is not None:

        if customer_id:
            existing_order.customer_id = customer_id

        if order_amount is not None:
            existing_order.amount = order_amount

        if order_currency:
            existing_order.currency = order_currency

        if order_status:
            current_status = (
                str(existing_order.status)
                if existing_order.status
                else None
            )

            incoming_status = str(
                order_status
            )

            # Do not downgrade a paid order.
            if not (
                current_status == "paid"
                and incoming_status != "paid"
            ):
                existing_order.status = (
                    incoming_status
                )

    # ==================================================
    # 7. PAYMENT
    # ==================================================

    if existing_payment is None and payment_id_str:

        payment_status = payment_entity.get(
            "status"
        )

        failure_reason = None

        if payload.get("event") == "payment.failed":
            failure_reason = (
                payment_entity.get(
                    "error_reason"
                )
                or payment_entity.get(
                    "error_description"
                )
                or payment_entity.get(
                    "error_code"
                )
            )

        existing_payment = Payment(
            payment_id=payment_id_str,
            customer_id=customer_id,
            order_id=order_id_str,
            amount=_amount_to_decimal(
                payment_entity.get("amount")
            ),
            currency=payment_entity.get(
                "currency"
            ),
            status=(
                str(payment_status)
                if payment_status
                else None
            ),
            failure_reason=(
                str(failure_reason)
                if failure_reason
                else None
            ),
            created_at=(
                _timestamp_to_datetime(
                    payment_entity.get("created_at")
                )
                or utc_now()
            ),
        )

        db.add(existing_payment)

    elif existing_payment is not None:

        if customer_id:
            existing_payment.customer_id = (
                customer_id
            )

        if order_id_str:
            existing_payment.order_id = (
                order_id_str
            )

        payment_amount = _amount_to_decimal(
            payment_entity.get("amount")
        )

        if payment_amount is not None:
            existing_payment.amount = (
                payment_amount
            )

        payment_currency = payment_entity.get(
            "currency"
        )

        if payment_currency:
            existing_payment.currency = (
                payment_currency
            )

        payment_status = payment_entity.get(
            "status"
        )

        if payment_status:
            existing_payment.status = (
                str(payment_status)
            )

        if payload.get("event") == "payment.failed":

            failure_reason = (
                payment_entity.get(
                    "error_reason"
                )
                or payment_entity.get(
                    "error_description"
                )
                or payment_entity.get(
                    "error_code"
                )
            )

            if failure_reason:
                existing_payment.failure_reason = (
                    str(failure_reason)
                )

    # ==================================================
    # 8. Return resolved identifiers
    # ==================================================

    return HistorySyncResult(
        customer_id=customer_id,
        order_id=order_id_str,
        payment_id=payment_id_str,
    )
