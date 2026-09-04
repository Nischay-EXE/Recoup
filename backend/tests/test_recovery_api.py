from decimal import Decimal
from unittest.mock import MagicMock, patch

from uuid import uuid4

from app.db.database import SessionLocal
from app.db.recovery_models import RecoveryCase, RecoveryEscalation
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_recovery_metrics_endpoint():
    expected = {
        "total_cases": 5,
        "recovered_cases": 2,
        "escalated_cases": 1,
        "unresolved_cases": 2,
        "amount_at_risk": Decimal("1000.00"),
        "amount_recovered": Decimal("600.00"),
        "total_attempts": 8,
        "recovery_rate": Decimal("60.00"),
    }

    with patch(
        "app.api.recovery.get_recovery_metrics",
        return_value=expected,
    ):
        response = client.get("/recovery/metrics")

    assert response.status_code == 200

    data = response.json()

    assert data["total_cases"] == 5
    assert data["recovered_cases"] == 2
    assert data["amount_at_risk"] == 1000.0
    assert data["amount_recovered"] == 600.0
    assert data["recovery_rate"] == 60.0


def test_recovery_breakdowns_endpoint():
    expected = {
        "by_revenue_object": {
            "payment": {
                "attempts": 2,
                "recovered_attempts": 1,
                "amount_recovered": Decimal("500.00"),
            }
        },
        "by_action": {},
        "by_channel": {},
    }

    with patch(
        "app.api.recovery.get_recovery_breakdowns",
        return_value=expected,
    ):
        response = client.get(
            "/recovery/metrics/breakdowns"
        )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["by_revenue_object"]["payment"]["attempts"]
        == 2
    )


def test_recovery_case_timeline_endpoint():
    expected = {
        "case_id": "case_001",
        "customer_id": "cust_001",
        "revenue_object_type": "payment",
        "amount_at_risk": Decimal("1000.00"),
        "amount_recovered": Decimal("1000.00"),
        "status": "recovered",
        "timeline": [],
    }

    with patch(
        "app.api.recovery.get_recovery_case_timeline",
        return_value=expected,
    ):
        response = client.get(
            "/recovery/cases/case_001/timeline"
        )

    assert response.status_code == 200
    assert response.json()["case_id"] == "case_001"
    assert response.json()["status"] == "recovered"


def test_recovery_case_timeline_returns_404_for_missing_case():
    with patch(
        "app.api.recovery.get_recovery_case_timeline",
        side_effect=ValueError(
            "Recovery case not found: missing"
        ),
    ):
        response = client.get(
            "/recovery/cases/missing/timeline"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Recovery case not found: missing"
    )


def test_recovery_case_escalation_endpoint():
    case_id = f"case_api_escalation_{uuid4().hex}"

    db = SessionLocal()

    try:
        case = RecoveryCase(
            case_id=case_id,
            revenue_object_type="invoice",
            customer_id="cust_api_001",
            amount_at_risk=Decimal("45000.00"),
            amount_recovered=Decimal("12000.00"),
            status="escalated",
        )
        db.add(case)

        escalation = RecoveryEscalation(
            case_id=case_id,
            reason_code="recovery_exhausted",
            summary="Recovery exhausted after automated attempts.",
            diagnosis="Multiple automated recovery attempts failed.",
            recommended_action=(
                "Contact the customer's accounts-payable or finance contact."
            ),
            priority="high",
            assigned_team="accounts_receivable",
            status="open",
        )
        db.add(escalation)
        db.commit()
    finally:
        db.close()

    response = client.get(
        f"/recovery/cases/{case_id}/escalation"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["case_id"] == case_id
    assert data["status"] == "open"
    assert data["reason_code"] == "recovery_exhausted"
    assert data["priority"] == "high"
    assert data["assigned_team"] == "accounts_receivable"

    assert data["amount_at_risk"] == 45000
    assert data["amount_recovered"] == 12000
    assert data["amount_remaining"] == 33000

    assert "Recovery exhausted" in data["summary"]
    assert "accounts-payable" in data["recommended_action"]

def test_assign_recovery_case_escalation():
    case_id = f"case_api_assignment_{uuid4().hex}"

    db = SessionLocal()

    try:
        case = RecoveryCase(
            case_id=case_id,
            revenue_object_type="invoice",
            customer_id="cust_assignment_001",
            amount_at_risk=Decimal("30000.00"),
            amount_recovered=Decimal("0.00"),
            status="escalated",
        )
        db.add(case)

        escalation = RecoveryEscalation(
            case_id=case_id,
            reason_code="recovery_exhausted",
            summary="Recovery exhausted.",
            diagnosis="Automated recovery attempts failed.",
            recommended_action="Contact the customer.",
            priority="high",
            assigned_team="accounts_receivable",
            status="open",
        )
        db.add(escalation)
        db.commit()
    finally:
        db.close()

    response = client.patch(
        f"/recovery/cases/{case_id}/escalation/assignment",
        json={
            "assigned_team": "customer_success",
            "assigned_to": "support.agent@company.com",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["case_id"] == case_id
    assert data["assigned_team"] == "customer_success"
    assert data["assigned_to"] == "support.agent@company.com"
    assert data["status"] == "open"


def test_assign_recovery_case_escalation_rejects_resolved():
    case_id = f"case_api_resolved_assignment_{uuid4().hex}"

    db = SessionLocal()

    try:
        case = RecoveryCase(
            case_id=case_id,
            revenue_object_type="payment",
            customer_id="cust_assignment_002",
            amount_at_risk=Decimal("5000.00"),
            amount_recovered=Decimal("5000.00"),
            status="resolved",
        )
        db.add(case)

        escalation = RecoveryEscalation(
            case_id=case_id,
            reason_code="recovery_exhausted",
            summary="Recovery case resolved.",
            diagnosis="Case already resolved.",
            recommended_action="No further action required.",
            priority="high",
            assigned_team="payments",
            status="resolved",
        )
        db.add(escalation)
        db.commit()
    finally:
        db.close()

    response = client.patch(
        f"/recovery/cases/{case_id}/escalation/assignment",
        json={
            "assigned_team": "customer_success",
            "assigned_to": "support.agent@company.com",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Cannot assign a resolved escalation"
    )

def test_add_recovery_case_escalation_note():
    case_id = f"case_api_note_{uuid4().hex}"

    db = SessionLocal()

    try:
        case = RecoveryCase(
            case_id=case_id,
            revenue_object_type="invoice",
            customer_id="cust_note_001",
            amount_at_risk=Decimal("10000.00"),
            amount_recovered=Decimal("0.00"),
            status="escalated",
        )
        db.add(case)

        escalation = RecoveryEscalation(
            case_id=case_id,
            reason_code="recovery_exhausted",
            summary="Recovery exhausted.",
            diagnosis="Automated recovery failed.",
            recommended_action="Contact customer.",
            priority="high",
            assigned_team="accounts_receivable",
            status="open",
        )
        db.add(escalation)
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/recovery/cases/{case_id}/escalation/notes",
        json={
            "note": "Customer confirmed payment will be made tomorrow.",
            "created_by": "support.agent@company.com",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["case_id"] == case_id
    assert data["note"] == (
        "Customer confirmed payment will be made tomorrow."
    )
    assert data["created_by"] == "support.agent@company.com"
    assert data["id"] is not None
    assert data["created_at"] is not None


def test_add_recovery_case_escalation_note_rejects_empty_note():
    case_id = f"case_api_empty_note_{uuid4().hex}"

    db = SessionLocal()

    try:
        case = RecoveryCase(
            case_id=case_id,
            revenue_object_type="payment",
            customer_id="cust_note_002",
            amount_at_risk=Decimal("5000.00"),
            amount_recovered=Decimal("0.00"),
            status="escalated",
        )
        db.add(case)

        escalation = RecoveryEscalation(
            case_id=case_id,
            reason_code="recovery_exhausted",
            summary="Recovery exhausted.",
            diagnosis="Automated recovery failed.",
            recommended_action="Contact customer.",
            priority="high",
            assigned_team="payments",
            status="open",
        )
        db.add(escalation)
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/recovery/cases/{case_id}/escalation/notes",
        json={
            "note": "   ",
            "created_by": "support.agent@company.com",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Note cannot be empty"


def test_add_recovery_case_escalation_note_rejects_resolved():
    case_id = f"case_api_resolved_note_{uuid4().hex}"

    db = SessionLocal()

    try:
        case = RecoveryCase(
            case_id=case_id,
            revenue_object_type="payment",
            customer_id="cust_note_003",
            amount_at_risk=Decimal("5000.00"),
            amount_recovered=Decimal("5000.00"),
            status="resolved",
        )
        db.add(case)

        escalation = RecoveryEscalation(
            case_id=case_id,
            reason_code="recovery_exhausted",
            summary="Recovery resolved.",
            diagnosis="Case already resolved.",
            recommended_action="No further action required.",
            priority="high",
            assigned_team="payments",
            status="resolved",
        )
        db.add(escalation)
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/recovery/cases/{case_id}/escalation/notes",
        json={
            "note": "Trying to add a note after resolution.",
            "created_by": "support.agent@company.com",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Cannot add a note to a resolved escalation"
    )

def test_resolve_recovery_case_escalation():
    case_id = f"case_api_resolve_{uuid4().hex}"

    db = SessionLocal()

    try:
        case = RecoveryCase(
            case_id=case_id,
            revenue_object_type="payment",
            customer_id="cust_resolve_001",
            amount_at_risk=Decimal("8000.00"),
            amount_recovered=Decimal("8000.00"),
            status="escalated",
        )
        db.add(case)

        escalation = RecoveryEscalation(
            case_id=case_id,
            reason_code="recovery_exhausted",
            summary="Recovery exhausted.",
            diagnosis="Automated recovery attempts failed.",
            recommended_action="Contact customer.",
            priority="high",
            assigned_team="payments",
            assigned_to="support.agent@company.com",
            status="open",
        )
        db.add(escalation)
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/recovery/cases/{case_id}/escalation/resolve"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["case_id"] == case_id
    assert data["status"] == "resolved"
    assert data["resolved_at"] is not None


def test_resolve_recovery_case_escalation_is_idempotent():
    case_id = f"case_api_resolve_idempotent_{uuid4().hex}"

    db = SessionLocal()

    try:
        case = RecoveryCase(
            case_id=case_id,
            revenue_object_type="invoice",
            customer_id="cust_resolve_002",
            amount_at_risk=Decimal("15000.00"),
            amount_recovered=Decimal("15000.00"),
            status="resolved",
        )
        db.add(case)

        escalation = RecoveryEscalation(
            case_id=case_id,
            reason_code="recovery_exhausted",
            summary="Recovery already resolved.",
            diagnosis="Case was already resolved.",
            recommended_action="No further action required.",
            priority="high",
            assigned_team="accounts_receivable",
            status="resolved",
        )
        db.add(escalation)
        db.commit()
    finally:
        db.close()

    response = client.post(
        f"/recovery/cases/{case_id}/escalation/resolve"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["case_id"] == case_id
    assert data["status"] == "resolved"
    assert data["resolved_at"] is None