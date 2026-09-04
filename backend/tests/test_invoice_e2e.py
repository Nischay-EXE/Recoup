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


def test_invoice_expired_to_paid_end_to_end():
    db = SessionLocal()

    invoice_id = f"inv_e2e_{uuid.uuid4().hex}"
    customer_id = f"cust_invoice_e2e_{uuid.uuid4().hex}"

    expired_event_id = f"evt_invoice_expired_e2e_{uuid.uuid4().hex}"
    paid_event_id = f"evt_invoice_paid_e2e_{uuid.uuid4().hex}"

    try:
        # ==========================================================
        # 1. Create invoice.expired event
        # ==========================================================

        expired_event = Event(
            source="razorpay",
            event_id=expired_event_id,
            event_type="invoice.expired",
            payload={
                "event": "invoice.expired",
                "payload": {
                    "invoice": {
                        "entity": {
                            "id": invoice_id,
                            "customer_id": customer_id,
                            "amount": 25000,
                            "amount_paid": 0,
                            "amount_due": 25000,
                            "currency": "INR",
                            "status": "expired",
                        }
                    }
                },
            },
        )

        expired_normalized = NormalizedEvent(
            event_id=expired_event_id,
            source="razorpay",
            event_type="invoice_expired",
            customer_id=customer_id,
            payment_id=None,
            order_id=None,
            subscription_id=None,
            invoice_id=invoice_id,
            amount=Decimal("250.00"),
            amount_paid=Decimal("0.00"),
            amount_due=Decimal("250.00"),
            currency="INR",
            status="expired",
        )

        db.add(expired_event)
        db.add(expired_normalized)
        db.commit()

        # ==========================================================
        # 2. Run the real worker recovery pipeline
        #
        # AI and external execution are mocked.
        # Context, case, guardrail, attempt and worker orchestration
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
                failure_analysis="Invoice has expired without payment.",
                customer_analysis="No prior recovery history is available.",
                recovery_factors=[
                    "Invoice remains unpaid.",
                    "Invoice has expired.",
                ],
                risk_level="medium",
                considerations=[
                    "A B2B payment recovery action may be appropriate."
                ],
            )

            propose.return_value = AgentDecision(
                action="send_payment_link",
                channel="email",
                reason="Invoice has expired without payment.",
                confidence=0.90,
                priority="high",
            )

            execute.return_value = ExecutionResult(
                success=True,
                status="sent",
                action="send_payment_link",
                channel="email",
                provider="mock_executor",
                message="Invoice payment recovery link sent.",
            )

            process_event(expired_event_id)

        # ==========================================================
        # 3. Verify invoice recovery attempt
        # ==========================================================

        attempt = (
            db.query(RecoveryAttempt)
            .filter(
                RecoveryAttempt.event_id == expired_event_id
            )
            .first()
        )

        assert attempt is not None
        assert attempt.invoice_id == invoice_id
        assert attempt.subscription_id is None
        assert attempt.payment_id is None
        assert attempt.order_id is None
        assert attempt.action == "send_payment_link"
        assert attempt.channel == "email"
        assert attempt.status == "sent"
        assert attempt.amount_at_risk == Decimal("250.00")

        # ==========================================================
        # 4. Verify invoice recovery case
        # ==========================================================

        case = (
            db.query(RecoveryCase)
            .filter(
                RecoveryCase.case_id == attempt.case_id
            )
            .first()
        )

        assert case is not None
        assert case.revenue_object_type == "invoice"
        assert case.invoice_id == invoice_id
        assert case.subscription_id is None
        assert case.current_payment_id is None

        # ==========================================================
        # 5. Create invoice.paid outcome
        # ==========================================================

        paid_event = Event(
            source="razorpay",
            event_id=paid_event_id,
            event_type="invoice.paid",
            payload={
                "event": "invoice.paid",
                "payload": {
                    "invoice": {
                        "entity": {
                            "id": invoice_id,
                            "customer_id": customer_id,
                            "amount": 25000,
                            "amount_paid": 25000,
                            "amount_due": 0,
                            "currency": "INR",
                            "status": "paid",
                        }
                    }
                },
            },
        )

        paid_normalized = NormalizedEvent(
            event_id=paid_event_id,
            source="razorpay",
            event_type="invoice_paid",
            customer_id=customer_id,
            payment_id=None,
            order_id=None,
            subscription_id=None,
            invoice_id=invoice_id,
            amount=Decimal("250.00"),
            amount_paid=Decimal("250.00"),
            amount_due=Decimal("0.00"),
            currency="INR",
            status="paid",
        )

        db.add(paid_event)
        db.add(paid_normalized)
        db.commit()

        # ==========================================================
        # 6. Process invoice.paid through the real worker
        # ==========================================================

        process_event(paid_event_id)

        # ==========================================================
        # 7. Verify recovery attempt succeeded
        # ==========================================================

        db.refresh(attempt)

        assert attempt.status == "succeeded"
        assert attempt.amount_recovered == Decimal("250.00")

        # ==========================================================
        # 8. Verify recovery case succeeded
        # ==========================================================

        db.refresh(case)

        assert case.status == "recovered"
        assert case.amount_recovered == Decimal("250.00")
        assert case.invoice_id == invoice_id
        assert case.current_payment_id is None

        # ==========================================================
        # 9. Verify invoice correlation explicitly
        # ==========================================================

        correlated = find_recovery_attempt(
            db,
            invoice_id=invoice_id,
        )

        assert correlated is not None
        assert correlated.id == attempt.id

    finally:
        db.close()