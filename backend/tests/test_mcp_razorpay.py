import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.mcp.razorpay import RazorpayMCPClient, RazorpayMCPError
from app.agent.executor_agent import (
    _extract_mcp_payment_link,
    _parse_mcp_result,
)


# --------------------------------------------------
# MCP capability boundary
# --------------------------------------------------


def test_mcp_allowed_tools_are_explicit():
    expected = {
        "create_payment_link",
        "payment_link_notify",
        "fetch_all_payment_links",
        "fetch_payment_link",
        "fetch_payment",
        "fetch_order",
    }

    assert RazorpayMCPClient.ALLOWED_TOOLS == expected


def test_mcp_blocks_unsupported_tool():
    client = object.__new__(RazorpayMCPClient)
    client._tools = {}

    with pytest.raises(RazorpayMCPError, match="not allowed"):
        client.get_tool("capture_payment")


# --------------------------------------------------
# MCP response parsing
# --------------------------------------------------


def test_parse_mcp_success_response():
    result = {
        "status": "success",
        "toolUseId": "revenue-recovery-fetch_all_payment_links",
        "content": [
            {
                "text": json.dumps(
                    {
                        "payment_links": [],
                    }
                )
            }
        ],
        "isError": False,
    }

    parsed = _parse_mcp_result(result)

    assert parsed == {
        "payment_links": [],
    }


def test_parse_mcp_error_response():
    result = {
        "status": "error",
        "toolUseId": "revenue-recovery-create_payment_link",
        "content": [
            {
                "text": "payment link already exists",
            }
        ],
        "isError": True,
    }

    with pytest.raises(
        RazorpayMCPError,
        match="MCP tool execution failed",
    ):
        _parse_mcp_result(result)


def test_extract_mcp_payment_link():
    parsed = {
        "payment_links": [
            {
                "id": "plink_test123",
                "short_url": "https://rzp.io/test",
                "reference_id": "rr-attempt-123",
            }
        ]
    }

    link = _extract_mcp_payment_link(parsed)

    assert link is not None
    assert link["id"] == "plink_test123"
    assert link["reference_id"] == "rr-attempt-123"


def test_extract_mcp_payment_link_returns_none_when_empty():
    parsed = {
        "payment_links": [],
    }

    assert _extract_mcp_payment_link(parsed) is None


# --------------------------------------------------
# MCP client invocation contract
# --------------------------------------------------


def test_mcp_client_passes_tool_use_id_and_name():
    client = object.__new__(RazorpayMCPClient)

    client._tools = {
        "fetch_payment_link": MagicMock(),
    }

    client._client = MagicMock()

    expected = {
        "status": "success",
        "content": [],
        "isError": False,
    }

    client._client.call_tool_sync.return_value = expected

    result = client.call_tool(
        "fetch_payment_link",
        {
            "payment_link_id": "plink_test123",
        },
    )

    assert result == expected

    client._client.call_tool_sync.assert_called_once_with(
        "revenue-recovery-fetch_payment_link",
        "fetch_payment_link",
        {
            "payment_link_id": "plink_test123",
        },
    )
