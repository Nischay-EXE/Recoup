import uuid
from unittest.mock import patch
from decimal import Decimal
from app.db.recovery_models import RecoveryAttempt, RecoveryDecisionRecord
from app.state.correlation import find_recovery_attempt
from app.db.database import SessionLocal
from app.db.recovery_models import RecoveryAttempt, RecoveryDecisionRecord
from app.state.attempts import create_recovery_attempt
from app.state.case_service import get_or_create_recovery_case
from app.state.context import RecoveryContext
from app.state.outcomes import mark_recovery_succeeded

def test_subscription_pending_creates_recovery_decision():
    from app.agent.schema import AgentDecision, AnalystReport
    from app.state.service import create_recovery_decision

    db = SessionLocal()

    try:
        event_id = f"evt_subscription_decision_{uuid.uuid4().hex}"
        subscription_id = f"sub_decision_{uuid.uuid4().hex}"

        context = RecoveryContext(
            event_id=event_id,
            event_type="subscription_pending",
            case_id=None,
            amount=Decimal("999.00"),
            currency="INR",
            payment_status="pending",
            customer_id=f"cust_decision_{uuid.uuid4().hex}",
            revenue_object_type="subscription",
            subscription_id=subscription_id,
            invoice_id=None,
        )

        analyst_report = AnalystReport(
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

        strategy = AgentDecision(
            action="send_payment_link",
            channel="email",
            reason="Subscription payment is pending.",
            confidence=0.90,
            priority="high",
        )

        with (
            patch(
                "app.state.service.analyze_recovery_context",
                return_value=analyst_report,
            ) as analyze,
            patch(
                "app.state.service.propose_strategy",
                return_value=strategy,
            ) as propose,
        ):
            result = create_recovery_decision(
                context=context,
                db=db,
            )

        assert result.event_id == event_id
        assert result.action == "send_payment_link"
        assert result.channel == "email"
        assert float(result.confidence) == 0.90
        assert result.priority == "high"

        analyze.assert_called_once_with(context)
        propose.assert_called_once_with(
            context=context,
            analyst_report=analyst_report,
        )

        persisted = (
            db.query(RecoveryDecisionRecord)
            .filter(
                RecoveryDecisionRecord.event_id == event_id
            )
            .first()
        )

        assert persisted is not None
        assert persisted.action == "send_payment_link"

    finally:
        db.close()


def test_subscription_only_recovery_marks_case_recovered():
    db = SessionLocal()

    try:
        subscription_id = f"sub_recovery_{uuid.uuid4().hex}"
        customer_id = f"cust_recovery_{uuid.uuid4().hex}"

        case = get_or_create_recovery_case(
            db,
            customer_id=customer_id,
            order_id=None,
            payment_id=None,
            amount=Decimal("999.00"),
            revenue_object_type="subscription",
            subscription_id=subscription_id,
            invoice_id=None,
        )

        attempt = RecoveryAttempt(
            event_id=f"evt_recovery_{uuid.uuid4().hex}",
            case_id=case.case_id,
            payment_id=None,
            order_id=None,
            subscription_id=subscription_id,
            invoice_id=None,
            customer_id=customer_id,
            action="send_payment_link",
            channel="email",
            ai_reason="Subscription requires recovery",
            ai_confidence=0.90,
            policy_result="approved",
            policy_reason="Allowed",
            attempt_number=1,
            status="sent",
            amount_at_risk=Decimal("999.00"),
            amount_recovered=Decimal("0.00"),
        )

        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        result = mark_recovery_succeeded(
            attempt=attempt,
            db=db,
            amount_recovered=Decimal("999.00"),
        )

        assert result.status == "succeeded"
        assert result.amount_recovered == Decimal("999.00")

        db.refresh(case)

        assert case.status == "recovered"
        assert case.amount_recovered == Decimal("999.00")
        assert case.subscription_id == subscription_id
        assert case.current_payment_id is None

    finally:
        db.close()

def test_two_active_attempts_for_same_subscription_are_ambiguous():
    db = SessionLocal()

    try:
        subscription_id = f"sub_ambiguous_{uuid.uuid4().hex}"
        customer_id = f"cust_ambiguous_{uuid.uuid4().hex}"

        case = get_or_create_recovery_case(
            db,
            customer_id=customer_id,
            order_id=None,
            payment_id=None,
            amount=Decimal("999.00"),
            revenue_object_type="subscription",
            subscription_id=subscription_id,
            invoice_id=None,
        )

        attempt_1 = RecoveryAttempt(
            event_id=f"evt_ambiguous_{uuid.uuid4().hex}_001",
            case_id=case.case_id,
            payment_id=None,
            order_id=None,
            subscription_id=subscription_id,
            invoice_id=None,
            customer_id=customer_id,
            action="send_payment_link",
            channel="email",
            ai_reason="Subscription requires recovery",
            ai_confidence=0.90,
            policy_result="approved",
            policy_reason="Allowed",
            attempt_number=1,
            status="sent",
            amount_at_risk=Decimal("999.00"),
            amount_recovered=Decimal("0.00"),
        )

        attempt_2 = RecoveryAttempt(
            event_id=f"evt_ambiguous_{uuid.uuid4().hex}_002",
            case_id=case.case_id,
            payment_id=None,
            order_id=None,
            subscription_id=subscription_id,
            invoice_id=None,
            customer_id=customer_id,
            action="send_payment_link",
            channel="email",
            ai_reason="Subscription requires recovery",
            ai_confidence=0.90,
            policy_result="approved",
            policy_reason="Allowed",
            attempt_number=2,
            status="sent",
            amount_at_risk=Decimal("999.00"),
            amount_recovered=Decimal("0.00"),
        )

        db.add_all([attempt_1, attempt_2])
        db.commit()

        # The outcome only identifies the subscription.
        # Because two active/correlatable attempts exist,
        # correlation must refuse to guess which attempt is correct.
        result = find_recovery_attempt(
            db,
            subscription_id=subscription_id,
        )

        assert result is None

        # Neither attempt should have been changed.
        db.refresh(attempt_1)
        db.refresh(attempt_2)

        assert attempt_1.status == "sent"
        assert attempt_2.status == "sent"

    finally:
        db.close()

def test_subscription_charged_for_wrong_subscription_does_not_correlate():
    db = SessionLocal()

    try:
        case = get_or_create_recovery_case(
            db,
            customer_id="cust_wrong_subscription_test",
            order_id=None,
            payment_id=None,
            amount=Decimal("999.00"),
            revenue_object_type="subscription",
            subscription_id="sub_A",
            invoice_id=None,
        )

        attempt = RecoveryAttempt(
           event_id = "evt_subscription_pending_multiple_20260904_001",
            case_id=case.case_id,
            payment_id=None,
            order_id=None,
            subscription_id="sub_A",
            invoice_id=None,
            customer_id="cust_wrong_subscription_test",
            action="send_payment_link",
            channel="email",
            ai_reason="Subscription requires recovery",
            ai_confidence=0.90,
            policy_result="approved",
            policy_reason="Allowed",
            attempt_number=1,
            status="sent",
            amount_at_risk=Decimal("999.00"),
            amount_recovered=Decimal("0.00"),
        )

        db.add(attempt)
        db.commit()

        # Outcome belongs to a completely different subscription.
        result = find_recovery_attempt(
            db,
            subscription_id="sub_B",
        )

        assert result is None

    finally:
        db.close()
def test_new_subscription_pending_event_does_not_reuse_old_active_attempt():
    db = SessionLocal()

    try:
        subscription_id = "sub_test_multiple_events_001"

        context_1 = RecoveryContext(
           event_id=f"evt_subscription_pending_{uuid.uuid4().hex}_001",
            event_type="subscription_pending",
            amount=Decimal("999.00"),
            currency="INR",
            payment_status="pending",
            customer_id="cust_subscription_multiple_events",
            revenue_object_type="subscription",
            subscription_id=subscription_id,
        )

        case = get_or_create_recovery_case(
            db,
            customer_id=context_1.customer_id,
            order_id=None,
            payment_id=None,
            amount=context_1.amount,
            revenue_object_type="subscription",
            subscription_id=subscription_id,
            invoice_id=None,
        )

        context_1.case_id = case.case_id

        decision_1 = RecoveryDecisionRecord(
            event_id=context_1.event_id,
            action="send_payment_link",
            channel="email",
            reason="Subscription requires recovery",
            message="Please complete your payment.",
            confidence=0.90,
            priority="high",
        )

        db.add(decision_1)
        db.commit()
        db.refresh(decision_1)

        attempt_1 = create_recovery_attempt(
            context_1,
            decision_1,
            db,
        )

        # A genuinely new subscription.pending event.
        context_2 = RecoveryContext(
            event_id=f"evt_subscription_pending_{uuid.uuid4().hex}_002",
            event_type="subscription_pending",
            case_id=case.case_id,
            amount=Decimal("999.00"),
            currency="INR",
            payment_status="pending",
            customer_id="cust_subscription_multiple_events",
            revenue_object_type="subscription",
            subscription_id=subscription_id,
        )

        decision_2 = RecoveryDecisionRecord(
            event_id=context_2.event_id,
            action="send_payment_link",
            channel="email",
            reason="Subscription requires recovery",
            message="Please complete your payment.",
            confidence=0.90,
            priority="high",
        )

        db.add(decision_2)
        db.commit()
        db.refresh(decision_2)

        attempt_2 = create_recovery_attempt(
            context_2,
            decision_2,
            db,
        )

        # This test intentionally documents current behavior:
        # a new event is allowed to create a new attempt.
        assert attempt_2.id != attempt_1.id
        assert attempt_2.attempt_number == attempt_1.attempt_number + 1
        assert attempt_2.subscription_id == subscription_id

    finally:
        db.close()


