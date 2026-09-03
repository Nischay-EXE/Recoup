from decimal import Decimal

from app.db.database import SessionLocal
from app.state.case_service import (
    get_or_create_recovery_case,
    register_payment_attempt,
    mark_case_recovered,
)


db = SessionLocal()

try:
    print("\n=== 1. CREATE RECOVERY CASE ===")

    case = get_or_create_recovery_case(
        db,
        customer_id="cust_case_test_001",
        order_id="order_case_test_001",
        payment_id="pay_failed_case_test_001",
        amount=Decimal("499.00"),
    )

    print("CASE ID:", case.case_id)
    print("ORIGINAL PAYMENT:", case.original_payment_id)
    print("CURRENT PAYMENT:", case.current_payment_id)
    print("STATUS:", case.status)
    print("AMOUNT AT RISK:", case.amount_at_risk)
    print("AMOUNT RECOVERED:", case.amount_recovered)


    print("\n=== 2. REGISTER NEW PAYMENT ===")

    case = register_payment_attempt(
        db,
        case,
        payment_id="pay_retry_case_test_001",
    )

    print("ORIGINAL PAYMENT:", case.original_payment_id)
    print("CURRENT PAYMENT:", case.current_payment_id)


    print("\n=== 3. MARK RECOVERED ===")

    case = mark_case_recovered(
        db,
        case,
        payment_id="pay_retry_case_test_001",
        amount_recovered=Decimal("499.00"),
    )

    print("STATUS:", case.status)
    print("CURRENT PAYMENT:", case.current_payment_id)
    print("AMOUNT RECOVERED:", case.amount_recovered)
    print("RESOLVED AT:", case.resolved_at)

finally:
    db.close()