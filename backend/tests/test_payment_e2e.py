import uuid
from decimal import Decimal
from unittest.mock import patch

from app.agent.executor_agent import ExecutionResult
from app.agent.schema import AgentDecision, AnalystReport
from app.db.database import SessionLocal
from app.db.models import Event
from app.db.normalized_models import NormalizedEvent
from app.db.recovery_models import RecoveryAttempt, RecoveryCase
from app.state.correlation import find_recovery_attempt
from app.worker.recovery_worker import process_event


def test_payment_failed_to_captured_end_to_end():
    db = SessionLocal()

    payment_id = f"pay_e2e_{uuid.uuid4().hex}"
    order_id = f"order_e2e_{uuid.uuid4().hex}"
    customer_id = f"cust_payment_e2e_{uuid.uuid4().hex}"

    failed_event_id = f"evt_payment_failed_e2e_{uuid.uuid4().hex}"
    captured_event_id = f"evt_payment_captured_e2e_{uuid.uuid4().hex}"

    try:
        # ==========================================================
        # 1. Create payment.failed event
        # ==========================================================

        failed_event = Event(
            source="razorpay",
            event_id=failed_event_id,
            event_type="payment.failed",
            payload={
                "event": "payment.failed",
                "payload": {
                    "payment": {
                        "entity": {
                            "id": payment_id,
                            "order_id": order_id,
                            "customer_id": customer_id,
                            "amount": 139500,
                            "currency": "INR",
                            "status": "failed",
                        }
                    }
                },
            },
        )

        failed_normalized = NormalizedEvent(
            event_id=failed_event_id,
            source="razorpay",
            event_type="payment_failed",
            customer_id=customer_id,
            payment_id=payment_id,
            order_id=order_id,
            subscription_id=None,
            invoice_id=None,
            amount=Decimal("1395.00"),
            currency="INR",
            status="failed",
        )

        db.add(failed_event)
        db.add(failed_normalized)
        db.commit()

        # ==========================================================
        # 2. Run actual recovery pipeline
        #
        # AI + external execution are mocked.
        # Worker, context, case, guardrail and attempt logic
        # execute for real.
        # ==========================================================

        with (
            patch(
                "app.state.service.analyze_recovery_context"
            ) as analyze,
            patch(
                "app.state.service.propose_strategy"
            ) as propose,
            patch(
                "app.state.executor.execute_strategy"
            ) as execute,
        ):
            analyze.return_value = AnalystReport(
                failure_analysis="Payment failed and remains unpaid.",
                customer_analysis="Customer has an outstanding payment.",
                recovery_factors=[
                    "Payment failed.",
                    "Order remains unpaid.",
                ],
                risk_level="medium",
                considerations=[
                    "A payment recovery action is appropriate."
                ],
            )

            propose.return_value = AgentDecision(
                action="send_payment_link",
                channel="email",
                reason="Payment failed and recovery is viable.",
                confidence=0.90,
                priority="high",
            )

            execute.return_value = ExecutionResult(
                success=True,
                status="sent",
                action="send_payment_link",
                channel="email",
                provider="mock_executor",
                message="Payment recovery link sent.",
            )

            process_event(failed_event_id)

        # ==========================================================
        # 3. Verify recovery attempt
        # ==========================================================

        attempt = (
            db.query(RecoveryAttempt)
            .filter(
                RecoveryAttempt.event_id == failed_event_id
            )
            .first()
        )

        assert attempt is not None
        assert attempt.payment_id == payment_id
        assert attempt.order_id == order_id
        assert attempt.subscription_id is None
        assert attempt.invoice_id is None
        assert attempt.action == "send_payment_link"
        assert attempt.channel == "email"
        assert attempt.status == "sent"
        assert attempt.amount_at_risk == Decimal("1395.00")

        # ==========================================================
        # 4. Verify payment recovery case
        # ==========================================================

        case = (
            db.query(RecoveryCase)
            .filter(
                RecoveryCase.case_id == attempt.case_id
            )
            .first()
        )

        assert case is not None
        assert case.revenue_object_type == "payment"
        assert case.current_payment_id == payment_id
        assert case.order_id == order_id
        assert case.customer_id == customer_id
        assert case.amount_at_risk == Decimal("1395.00")
        assert case.amount_recovered == Decimal("0.00")

        # ==========================================================
        # 5. Create payment.captured outcome
        # ==========================================================

        captured_event = Event(
            source="razorpay",
            event_id=captured_event_id,
            event_type="payment.captured",
            payload={
                "event": "payment.captured",
                "payload": {
                    "payment": {
                        "entity": {
                            "id": payment_id,
                            "order_id": order_id,
                            "customer_id": customer_id,
                            "amount": 139500,
                            "currency": "INR",
                            "status": "captured",
                        }
                    }
                },
            },
        )

        captured_normalized = NormalizedEvent(
            event_id=captured_event_id,
            source="razorpay",
            event_type="payment_captured",
            customer_id=customer_id,
            payment_id=payment_id,
            order_id=order_id,
            subscription_id=None,
            invoice_id=None,
            amount=Decimal("1395.00"),
            currency="INR",
            status="captured",
        )

        db.add(captured_event)
        db.add(captured_normalized)
        db.commit()

        # ==========================================================
        # 6. Process outcome through actual worker
        # ==========================================================

        process_event(captured_event_id)

        # ==========================================================
        # 7. Verify attempt recovered
        # ==========================================================

        db.refresh(attempt)

        assert attempt.status == "succeeded"
        assert attempt.amount_recovered == Decimal("1395.00")

        # ==========================================================
        # 8. Verify case recovered
        # ==========================================================

        db.refresh(case)

        assert case.status == "recovered"
        assert case.amount_recovered == Decimal("1395.00")

        # ==========================================================
        # 9. Verify payment correlation
        # ==========================================================

        correlated = find_recovery_attempt(
            db,
            payment_id=payment_id,
        )

        assert correlated is not None
        assert correlated.id == attempt.id

    finally:
        db.close()
