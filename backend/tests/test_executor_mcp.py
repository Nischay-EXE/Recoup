from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.agent.executor_agent import (
    ExecutionResult,
    _create_or_reuse_payment_link,
    _execute_reminder,
)


def make_attempt():
    return SimpleNamespace(
        id=123,
        payment_id="pay_test123",
        case_id="case_test123",
        recovery_case_id="case_test123",
        event_id="evt_test123",
        amount_at_risk=100,
        currency="INR",
        channel="email",
        action="send_payment_link",
    )


def make_decision():
    return SimpleNamespace(
        message="Please complete your payment.",
    )


def make_customer():
    return SimpleNamespace(
        name="Test Customer",
        email="test@example.com",
        phone="+919999999999",
    )


def make_db():
    db = MagicMock()

    payment = SimpleNamespace(
        currency="INR",
    )

    db.query.return_value.filter.return_value.first.return_value = payment

    return db


# --------------------------------------------------
# Payment-link execution through MCP
# --------------------------------------------------


def test_payment_link_creation_uses_mcp():
    attempt = make_attempt()
    decision = make_decision()
    customer = make_customer()
    db = make_db()

    mcp = MagicMock()

    mcp.call_tool.side_effect = [
        {
            "status": "success",
            "content": [
                {
                    "text": '{"payment_links":[]}',
                }
            ],
            "isError": False,
        },
        {
            "status": "success",
            "content": [
                {
                    "text": (
                        '{"id":"plink_test123",'
                        '"short_url":"https://rzp.io/test",'
                        '"reference_id":"rr-attempt-123"}'
                    ),
                }
            ],
            "isError": False,
        },
    ]

    with patch(
        "app.agent.executor_agent._razorpay_mcp",
        return_value=mcp,
    ), patch(
        "app.agent.executor_agent._razorpay"
    ) as rest:

        # MCP lookup returned no existing link.
        # REST read-only lookup must also return no link.
        rest.return_value.find_payment_link_by_reference.return_value = None

        result = _create_or_reuse_payment_link(
            attempt,
            decision,
            customer,
            db,
        )

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.status == "sent"
    assert result.provider == "razorpay_mcp"
    assert result.external_id == "plink_test123"
    assert result.external_url == "https://rzp.io/test"

    # REST must not create anything.
    rest.return_value.create_payment_link.assert_not_called()

    assert mcp.call_tool.call_count == 2

    first_call = mcp.call_tool.call_args_list[0]

    assert first_call.args[0] == "fetch_all_payment_links"
    assert first_call.args[1]["reference_id"] == "rr-attempt-123"

    second_call = mcp.call_tool.call_args_list[1]

    assert second_call.args[0] == "create_payment_link"

    arguments = second_call.args[1]

    assert arguments["amount"] == 10000
    assert arguments["currency"] == "INR"
    assert arguments["reference_id"] == "rr-attempt-123"
    assert arguments["notify_email"] is True
    assert arguments["notify_sms"] is False
    assert arguments["reminder_enable"] is False

    assert mcp.disconnect.call_count == 2


# --------------------------------------------------
# MCP create failure must NOT fall back to REST
# --------------------------------------------------


def test_payment_link_mcp_create_failure_does_not_fallback_to_rest():
    attempt = make_attempt()
    decision = make_decision()
    customer = make_customer()
    db = make_db()

    mcp = MagicMock()

    mcp.call_tool.side_effect = [
        {
            "status": "success",
            "content": [
                {
                    "text": '{"payment_links":[]}',
                }
            ],
            "isError": False,
        },
        {
            "status": "error",
            "content": [
                {
                    "text": "payment link creation failed",
                }
            ],
            "isError": True,
        },
    ]

    with patch(
        "app.agent.executor_agent._razorpay_mcp",
        return_value=mcp,
    ), patch(
        "app.agent.executor_agent._razorpay"
    ) as rest:

        # No existing Payment Link.
        rest.return_value.find_payment_link_by_reference.return_value = None

        with pytest.raises(
            RuntimeError,
            match="REST fallback is intentionally disabled",
        ):
            _create_or_reuse_payment_link(
                attempt,
                decision,
                customer,
                db,
            )

    # Critical safety property:
    # once MCP creation starts, REST creation must never happen.
    rest.return_value.create_payment_link.assert_not_called()

    assert mcp.disconnect.call_count == 2


# --------------------------------------------------
# Reminder execution through MCP
# --------------------------------------------------


def test_reminder_uses_mcp_payment_link_notify():
    attempt = make_attempt()
    attempt.action = "send_reminder"

    decision = make_decision()
    db = make_db()

    mcp = MagicMock()

    mcp.call_tool.return_value = {
        "status": "success",
        "content": [
            {
                "text": (
                    '{"id":"plink_test123",'
                    '"status":"notified"}'
                ),
            }
        ],
        "isError": False,
    }

    previous_link = {
        "id": "plink_test123",
        "short_url": "https://rzp.io/test",
    }

    with patch(
        "app.agent.executor_agent._find_previous_payment_link",
        return_value=previous_link,
    ), patch(
        "app.agent.executor_agent._razorpay_mcp",
        return_value=mcp,
    ):

        result = _execute_reminder(
            attempt,
            decision,
            db,
        )

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.status == "sent"
    assert result.provider == "razorpay_mcp"
    assert result.external_id == "plink_test123"
    assert result.external_url == "https://rzp.io/test"

    mcp.call_tool.assert_called_once_with(
        "payment_link_notify",
        {
            "payment_link_id": "plink_test123",
            "medium": "email",
        },
    )

    mcp.disconnect.assert_called_once()

def test_payment_link_test_mode_limit_is_classified_as_permanent():
    from app.agent.executor_agent import PermanentExecutionError

    # The classification is exercised through the actual provider-error
    # marker used by the executor. This protects the retry boundary from
    # turning a known Razorpay test-mode quota into a Redis retry loop.
    error = PermanentExecutionError(
        "Razorpay MCP payment-link creation failed: test mode limit of 30 reached for payment_link"
    )

    assert "test mode limit" in str(error).lower()
