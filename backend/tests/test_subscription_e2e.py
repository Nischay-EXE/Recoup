import uuid
from decimal import Decimal
from unittest.mock import patch

from app.db.database import SessionLocal
from app.db.models import Event
from app.db.normalized_models import NormalizedEvent
from app.db.recovery_models import RecoveryAttempt, RecoveryCase
from app.state.correlation import find_recovery_attempt
from app.worker.recovery_worker import process_event
from app.agent.executor_agent import ExecutionResult
from app.agent.schema import AgentDecision, AnalystReport

def test_subscription_pending_to_charged_end_to_end():
    db = SessionLocal()

    subscription_id = f"sub_e2e_{uuid.uuid4().hex}"
    customer_id = f"cust_e2e_{uuid.uuid4().hex}"

    pending_event_id = f"evt_sub_pending_e2e_{uuid.uuid4().hex}"
    charged_event_id = f"evt_sub_charged_e2e_{uuid.uuid4().hex}"

    try:
        # ==========================================================
        # 1. Create subscription.pending event
        # ==========================================================

        pending_event = Event(
            source="razorpay",
            event_id=pending_event_id,
            event_type="subscription.pending",
            payload={
                "event": "subscription.pending",
                "payload": {
                    "subscription": {
                        "entity": {
                            "id": subscription_id,
                            "customer_id": customer_id,
                            "status": "pending",
                        }
                    }
                },
            },
        )

        pending_normalized = NormalizedEvent(
            event_id=pending_event_id,
            source="razorpay",
            event_type="subscription_pending",
            customer_id=customer_id,
            payment_id=None,
            order_id=None,
            subscription_id=subscription_id,
            invoice_id=None,
            amount=Decimal("999.00"),
            currency="INR",
            status="pending",
        )

        db.add(pending_event)
        db.add(pending_normalized)
        db.commit()

        # ==========================================================
        # 2. Run the actual worker pipeline
        #
        # Mock only the AI + external execution boundary.
        # The worker, context, guardrail, case, and attempt logic
        # still execute for real.
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
            from app.agent.schema import AgentDecision, AnalystReport

            analyze.return_value = AnalystReport(
                failure_analysis="Subscription payment is pending.",
                customer_analysis="No prior recovery history is available.",
                recovery_factors=[
                    "Subscription payment remains pending."
                ],
                risk_level="medium",
                considerations=[
                    "A payment recovery action may be appropriate."
                ],
            )

            propose.return_value = AgentDecision(
                action="send_payment_link",
                channel="email",
                reason="Subscription payment is pending.",
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

            process_event(pending_event_id)

        # ==========================================================
        # 3. Verify recovery attempt was created and sent
        # ==========================================================

        attempt = (
            db.query(RecoveryAttempt)
            .filter(
                RecoveryAttempt.event_id == pending_event_id
            )
            .first()
        )

        assert attempt is not None
        assert attempt.subscription_id == subscription_id
        assert attempt.payment_id is None
        assert attempt.order_id is None
        assert attempt.action == "send_payment_link"
        assert attempt.channel == "email"
        assert attempt.status == "sent"
        assert attempt.amount_at_risk == Decimal("999.00")

        # ==========================================================
        # 4. Verify subscription recovery case
        # ==========================================================

        case = (
            db.query(RecoveryCase)
            .filter(
                RecoveryCase.case_id == attempt.case_id
            )
            .first()
        )

        assert case is not None
        assert case.revenue_object_type == "subscription"
        assert case.subscription_id == subscription_id
        assert case.current_payment_id is None

        # ==========================================================
        # 5. Create subscription.charged outcome
        #
        # The outcome identifies the subscription, so correlation
        # must happen through subscription_id.
        # ==========================================================

        charged_event = Event(
            source="razorpay",
            event_id=charged_event_id,
            event_type="subscription.charged",
            payload={
                "event": "subscription.charged",
                "payload": {
                    "subscription": {
                        "entity": {
                            "id": subscription_id,
                            "customer_id": customer_id,
                            "status": "active",
                        }
                    }
                },
            },
        )

        charged_normalized = NormalizedEvent(
            event_id=charged_event_id,
            source="razorpay",
            event_type="subscription_charged",
            customer_id=customer_id,
            payment_id=None,
            order_id=None,
            subscription_id=subscription_id,
            invoice_id=None,
            amount=Decimal("999.00"),
            currency="INR",
            status="charged",
        )

        db.add(charged_event)
        db.add(charged_normalized)
        db.commit()

        # ==========================================================
        # 6. Process the outcome through the actual worker
        # ==========================================================

        process_event(charged_event_id)

        # ==========================================================
        # 7. Verify recovery succeeded
        # ==========================================================

        db.refresh(attempt)

        assert attempt.status == "succeeded"
        assert attempt.amount_recovered == Decimal("999.00")

        # ==========================================================
        # 8. Verify the case was recovered
        # ==========================================================

        db.refresh(case)

        assert case.status == "recovered"
        assert case.amount_recovered == Decimal("999.00")
        assert case.subscription_id == subscription_id
        assert case.current_payment_id is None

        # ==========================================================
        # 9. Verify subscription correlation explicitly
        # ==========================================================

        correlated = find_recovery_attempt(
            db,
            subscription_id=subscription_id,
        )

        assert correlated is not None
        assert correlated.id == attempt.id

    finally:
        db.close()
