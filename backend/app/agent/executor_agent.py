import json
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable

from dotenv import load_dotenv
from strands import Agent
from strands.models.openai import OpenAIModel
from strands.tools.decorator import tool

from app.clients.razorpay import RazorpayClient
from app.config import settings
from app.db.history_models import Customer, Order, Payment
from app.db.recovery_models import RecoveryAttempt, RecoveryDecisionRecord
from app.mcp.razorpay import RazorpayMCPClient, RazorpayMCPError


# --------------------------------------------------
# Environment
# --------------------------------------------------

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is not configured in the environment."
    )


# --------------------------------------------------
# Supported execution contract
# --------------------------------------------------

SUPPORTED_ACTIONS = {
    "retry_payment",
    "send_payment_link",
    "send_reminder",
    "contact_support",
    "no_action",
}

SUPPORTED_CHANNELS = {
    "whatsapp",
    "email",
    "sms",
    "none",
}

SUPPORTED_REAL_PAYMENT_LINK_CHANNELS = {
    "email",
    "sms",
}


class PermanentExecutionError(RuntimeError):
    """Raised when a provider rejects execution for a non-transient reason."""


@dataclass
class ExecutionResult:
    """Deterministic result returned by the Executor tool layer."""

    success: bool
    status: str
    action: str
    channel: str
    provider: str | None = None
    external_id: str | None = None
    external_url: str | None = None
    message: str | None = None
    error: str | None = None


# --------------------------------------------------
# Groq / Strands configuration
# --------------------------------------------------

MODEL_ID = "qwen/qwen3.6-27b"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

groq_model = OpenAIModel(
    client_args={
        "api_key": GROQ_API_KEY,
        "base_url": GROQ_BASE_URL,
    },
    model_id=MODEL_ID,
    params={
        "temperature": 0.1,
        "max_tokens": 500,
        "reasoning_effort": "none",
    },
)


# --------------------------------------------------
# Utility functions
# --------------------------------------------------


def _razorpay() -> RazorpayClient:
    if not settings.razorpay_key_id:
        raise ValueError("RAZORPAY_KEY_ID is not configured.")

    if not settings.razorpay_key_secret:
        raise ValueError("RAZORPAY_KEY_SECRET is not configured.")

    return RazorpayClient(
        key_id=settings.razorpay_key_id,
        key_secret=settings.razorpay_key_secret,
    )


def _razorpay_mcp() -> RazorpayMCPClient:
    """
    Create and connect to the Razorpay Remote MCP capability boundary.

    RazorpayMCPClient owns credential configuration through settings.
    """
    client = RazorpayMCPClient()
    client.connect()
    return client


def _get_customer(
    attempt: RecoveryAttempt,
    db,
) -> Customer:
    if not attempt.customer_id:
        raise ValueError(
            "Recovery attempt has no customer_id."
        )

    customer = (
        db.query(Customer)
        .filter(
            Customer.customer_id == attempt.customer_id
        )
        .first()
    )

    if customer is None:
        raise ValueError(
            f"Customer not found: {attempt.customer_id}"
        )

    return customer


def _get_currency(
    attempt: RecoveryAttempt,
    db,
) -> str:
    if attempt.payment_id:
        payment = (
            db.query(Payment)
            .filter(
                Payment.payment_id == attempt.payment_id
            )
            .first()
        )

        if payment and payment.currency:
            return payment.currency.upper()

    if attempt.order_id:
        order = (
            db.query(Order)
            .filter(
                Order.order_id == attempt.order_id
            )
            .first()
        )

        if order and order.currency:
            return order.currency.upper()

    return "INR"


def _amount_minor(
    amount: Decimal | None,
    currency: str,
) -> int:
    if amount is None:
        raise ValueError(
            "Recovery amount is missing."
        )

    if currency.upper() != "INR":
        raise ValueError(
            "Current real Razorpay executor supports INR only. "
            f"Received currency={currency}."
        )

    try:
        value = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid recovery amount: {amount}"
        ) from exc

    if value <= 0:
        raise ValueError(
            "Recovery amount must be greater than zero."
        )

    minor = value * Decimal("100")

    if minor != minor.to_integral_value():
        raise ValueError(
            "INR recovery amount must have at most two decimals."
        )

    return int(minor)


def _reference(attempt_id: int) -> str:
    # <= 40 characters and deterministic per recovery attempt.
    return f"rr-attempt-{attempt_id}"


# --------------------------------------------------
# MCP response helpers
# --------------------------------------------------


def _parse_mcp_result(result) -> dict:
    """
    Convert the Razorpay MCP response envelope into its JSON payload.

    Example MCP response:

        {
            "status": "success",
            "toolUseId": "...",
            "content": [
                {
                    "text": "{\"payment_links\":[]}"
                }
            ],
            "isError": false
        }
    """

    if not isinstance(result, dict):
        raise RazorpayMCPError(
            "Unexpected MCP response type: "
            f"{type(result).__name__}"
        )

    if result.get("status") != "success" or result.get("isError"):
        raise RazorpayMCPError(
            f"MCP tool execution failed: {result!r}"
        )

    content = result.get("content")

    if not isinstance(content, list):
        raise RazorpayMCPError(
            "MCP response does not contain a valid content list."
        )

    for item in content:
        if not isinstance(item, dict):
            continue

        text = item.get("text")

        if not isinstance(text, str):
            continue

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RazorpayMCPError(
                "MCP response content is not valid JSON."
            ) from exc

        if isinstance(parsed, dict):
            return parsed

    raise RazorpayMCPError(
        "MCP response did not contain a JSON object."
    )


def _extract_mcp_payment_link(result) -> dict | None:
    """
    Extract one Payment Link object from a parsed Razorpay MCP response.
    """

    if not isinstance(result, dict):
        return None

    if result.get("id"):
        return result

    for key in (
        "payment_links",
        "items",
        "data",
    ):
        value = result.get(key)

        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and item.get("id"):
                    return item

        elif isinstance(value, dict) and value.get("id"):
            return value

    return None


# --------------------------------------------------
# Real execution primitives
# --------------------------------------------------


def _create_or_reuse_payment_link(
    attempt: RecoveryAttempt,
    decision: RecoveryDecisionRecord,
    customer: Customer,
    db,
) -> ExecutionResult:
    currency = _get_currency(attempt, db)
    reference_id = _reference(attempt.id)

    # --------------------------------------------------
    # 1. Check for an existing Payment Link through MCP.
    # --------------------------------------------------

    existing = None
    mcp_client = None

    try:
        mcp_client = _razorpay_mcp()

        lookup_result = mcp_client.call_tool(
            "fetch_all_payment_links",
            {
                "reference_id": reference_id,
            },
        )

        lookup_data = _parse_mcp_result(
            lookup_result
        )

        existing = _extract_mcp_payment_link(
            lookup_data
        )

        if existing is not None:
            payment_link_id = existing.get("id")
            short_url = existing.get("short_url")

            print(
                "[EXECUTOR TOOL] Reusing existing Razorpay Payment Link "
                "via MCP "
                f"attempt_id={attempt.id} "
                f"payment_link_id={payment_link_id}"
            )

            return ExecutionResult(
                success=True,
                status="sent",
                action=attempt.action,
                channel=attempt.channel,
                provider="razorpay_mcp",
                external_id=payment_link_id,
                external_url=short_url,
                message=decision.message,
            )

    except RazorpayMCPError as exc:
        print(
            "[EXECUTOR TOOL] Razorpay MCP lookup unavailable; "
            f"falling back to REST: {exc}"
        )

    finally:
        if mcp_client is not None:
            mcp_client.disconnect()

    # --------------------------------------------------
    # 2. Safe REST fallback for read-only lookup.
    # --------------------------------------------------

    if existing is None:
        existing = _razorpay().find_payment_link_by_reference(
            reference_id
        )

    if existing is not None:
        payment_link_id = existing.get("id")
        short_url = existing.get("short_url")

        print(
            "[EXECUTOR TOOL] Reusing existing Razorpay Payment Link "
            f"via REST "
            f"attempt_id={attempt.id} "
            f"payment_link_id={payment_link_id}"
        )

        return ExecutionResult(
            success=True,
            status="sent",
            action=attempt.action,
            channel=attempt.channel,
            provider="razorpay",
            external_id=payment_link_id,
            external_url=short_url,
            message=decision.message,
        )

    # --------------------------------------------------
    # 3. Validate the approved communication channel.
    # --------------------------------------------------

    if attempt.channel == "email":
        if not customer.email:
            raise ValueError(
                "Customer email is missing."
            )

        notify_email = True
        notify_sms = False

    elif attempt.channel == "sms":
        if not customer.phone:
            raise ValueError(
                "Customer phone is missing."
            )

        notify_email = False
        notify_sms = True

    else:
        raise ValueError(
            "Real Razorpay Payment Link execution supports "
            "email and sms only. "
            f"Received channel={attempt.channel}."
        )

    # --------------------------------------------------
    # 4. Validate amount.
    # --------------------------------------------------

    if attempt.amount_at_risk is None:
        raise ValueError(
            "Recovery attempt amount_at_risk is missing."
        )

    amount_minor = _amount_minor(
        attempt.amount_at_risk,
        currency,
    )

    # --------------------------------------------------
    # 5. Build provider metadata.
    # --------------------------------------------------

    notes = {
        "source": "revenue_recovery_agent",
        "recovery_attempt_id": str(attempt.id),
        "recovery_case_id": str(attempt.case_id or ""),
        "event_id": str(attempt.event_id),
    }

    print(
        "[EXECUTOR TOOL] Creating Razorpay Payment Link "
        "via MCP "
        f"attempt_id={attempt.id} "
        f"amount={attempt.amount_at_risk} "
        f"currency={currency} "
        f"channel={attempt.channel} "
        f"reference_id={reference_id}"
    )

    # --------------------------------------------------
    # 6. Create through Razorpay MCP.
    #
    # Do NOT automatically fall back to REST here.
    # If MCP has reached Razorpay and execution fails,
    # blindly retrying through REST could create a duplicate.
    # --------------------------------------------------

    mcp_client = None

    try:
        mcp_client = _razorpay_mcp()

        result = mcp_client.call_tool(
            "create_payment_link",
            {
                "amount": amount_minor,
                "currency": currency,
                "customer_name": customer.name,
                "customer_email": customer.email,
                "customer_contact": customer.phone,
                "reference_id": reference_id,
                "description": ("Outstanding payment for your recent transaction."),
                "notes": notes,
                "notify_email": notify_email,
                "notify_sms": notify_sms,
                "reminder_enable": False,
            },
        )

        data = _parse_mcp_result(
            result
        )

        link = _extract_mcp_payment_link(
            data
        )

        if link is None:
            raise RazorpayMCPError(
                "Razorpay MCP create_payment_link returned "
                "no Payment Link object."
            )

        print(
            "[EXECUTOR TOOL] Created Razorpay Payment Link "
            "via MCP "
            f"attempt_id={attempt.id} "
            f"payment_link_id={link.get('id')}"
        )

        return ExecutionResult(
            success=True,
            status="sent",
            action=attempt.action,
            channel=attempt.channel,
            provider="razorpay_mcp",
            external_id=link.get("id"),
            external_url=link.get("short_url"),
            message=decision.message,
        )

    except RazorpayMCPError as exc:
        error_text = str(exc)
        lowered = error_text.lower()
        permanent_markers = (
            "test mode limit",
            "limit of 30 reached",
            "quota exceeded",
            "not permitted",
            "permission denied",
            "invalid api key",
            "authentication failed",
            "invalid request",
        )
        message = (
            "Razorpay MCP payment-link creation failed. "
            "REST fallback is intentionally disabled after MCP execution "
            "begins to avoid duplicate payment links. "
            f"Provider error: {error_text}"
        )
        if any(marker in lowered for marker in permanent_markers):
            raise PermanentExecutionError(message) from exc
        raise RuntimeError(message) from exc

    finally:
        if mcp_client is not None:
            mcp_client.disconnect()


def _find_previous_payment_link(
    attempt: RecoveryAttempt,
    db,
) -> dict | None:
    if not attempt.case_id:
        return None

    previous = (
        db.query(RecoveryAttempt)
        .filter(
            RecoveryAttempt.case_id == attempt.case_id,
            RecoveryAttempt.id != attempt.id,
            RecoveryAttempt.action.in_(
                {
                    "send_payment_link",
                    "retry_payment",
                }
            ),
            RecoveryAttempt.status.in_(
                {
                    "sent",
                    "succeeded",
                }
            ),
        )
        .order_by(
            RecoveryAttempt.attempt_number.desc()
        )
        .first()
    )

    if previous is None:
        return None

    reference_id = _reference(previous.id)

    # --------------------------------------------------
    # Prefer MCP for read-only Payment Link lookup.
    # --------------------------------------------------

    mcp_client = None

    try:
        mcp_client = _razorpay_mcp()

        result = mcp_client.call_tool(
            "fetch_all_payment_links",
            {
                "reference_id": reference_id,
            },
        )

        data = _parse_mcp_result(
            result
        )

        link = _extract_mcp_payment_link(
            data
        )

        if link is not None:
            return link

    except RazorpayMCPError as exc:
        print(
            "[EXECUTOR TOOL] Razorpay MCP reminder lookup unavailable; "
            f"falling back to REST: {exc}"
        )

    finally:
        if mcp_client is not None:
            mcp_client.disconnect()

    # --------------------------------------------------
    # Safe REST fallback for read-only lookup.
    # --------------------------------------------------

    return _razorpay().find_payment_link_by_reference(
        reference_id
    )


def _execute_reminder(
    attempt: RecoveryAttempt,
    decision: RecoveryDecisionRecord,
    db,
) -> ExecutionResult:
    if attempt.channel not in {
        "email",
        "sms",
    }:
        raise ValueError(
            "send_reminder currently supports email and sms only."
        )

    link = _find_previous_payment_link(
        attempt,
        db,
    )

    if link is None:
        raise ValueError(
            "No previous recovery Payment Link was found "
            "for this reminder."
        )

    payment_link_id = link.get("id")

    if not payment_link_id:
        raise ValueError(
            "Previous Payment Link has no Razorpay id."
        )

    print(
        "[EXECUTOR TOOL] Sending Razorpay Payment Link reminder "
        "via MCP "
        f"attempt_id={attempt.id} "
        f"payment_link_id={payment_link_id} "
        f"medium={attempt.channel}"
    )

    # --------------------------------------------------
    # Use MCP for the actual notification.
    #
    # Do NOT automatically fall back to REST after MCP
    # execution begins because the notification may already
    # have been delivered.
    # --------------------------------------------------

    mcp_client = None

    try:
        mcp_client = _razorpay_mcp()

        result = mcp_client.call_tool(
            "payment_link_notify",
            {
                "payment_link_id": payment_link_id,
                "medium": attempt.channel,
            },
        )

        data = _parse_mcp_result(
            result
        )

        return ExecutionResult(
            success=True,
            status="sent",
            action=attempt.action,
            channel=attempt.channel,
            provider="razorpay_mcp",
            external_id=payment_link_id,
            external_url=link.get("short_url"),
            message=decision.message,
        )

    except RazorpayMCPError as exc:
        raise RuntimeError(
            "Razorpay MCP payment-link notification failed. "
            "REST fallback is intentionally disabled after MCP "
            "execution begins to avoid duplicate notifications."
        ) from exc

    finally:
        if mcp_client is not None:
            mcp_client.disconnect()


def _execute_support(
    attempt: RecoveryAttempt,
    decision: RecoveryDecisionRecord,
) -> ExecutionResult:
    print(
        "[EXECUTOR TOOL] Support escalation "
        f"attempt_id={attempt.id} "
        f"case_id={attempt.case_id}"
    )

    return ExecutionResult(
        success=True,
        status="escalated",
        action=attempt.action,
        channel=attempt.channel,
        provider="internal_support",
        external_id=f"support-attempt-{attempt.id}",
        message=decision.message,
    )


def _execute_no_action(
    attempt: RecoveryAttempt,
    decision: RecoveryDecisionRecord,
) -> ExecutionResult:
    print(
        "[EXECUTOR TOOL] No action "
        f"attempt_id={attempt.id}"
    )

    return ExecutionResult(
        success=True,
        status="stopped",
        action=attempt.action,
        channel=attempt.channel,
        provider="internal",
        message=decision.message,
    )


# --------------------------------------------------
# Tool factory
# --------------------------------------------------


def _make_tool(
    name: str,
    description: str,
    handler: Callable[[], ExecutionResult],
):
    """
    Create a Strands-compatible zero-argument tool.

    The tool closes over the already-verified execution data.
    """

    @tool(
        name=name,
        description=description,
    )
    def tool_function() -> str:
        try:
            result = handler()
        except PermanentExecutionError as exc:
            result = ExecutionResult(
                success=False,
                status="blocked",
                action="unknown",
                channel="unknown",
                provider="razorpay_mcp",
                error=str(exc),
            )
        except Exception as exc:
            result = ExecutionResult(
                success=False,
                status="execution_failed",
                action="unknown",
                channel="unknown",
                provider="executor_tool",
                error=f"{type(exc).__name__}: {exc}",
            )

        execution_state["result"] = result

        return json.dumps(
            {
                "success": result.success,
                "status": result.status,
                "provider": result.provider,
                "external_id": result.external_id,
                "external_url": result.external_url,
                "message": result.message,
                "error": result.error,
            }
        )

    return tool_function


# This mutable state is deliberately scoped to one execute_strategy() call
# and replaced before every Agent invocation.
execution_state: dict[str, ExecutionResult | None] = {
    "result": None,
}


# --------------------------------------------------
# Executor system prompt
# --------------------------------------------------

SYSTEM_PROMPT = """
You are the Recovery Executor Agent in a payment recovery system.

Your role is EXECUTION, not strategy.

The Recovery Strategist has already selected an action and communication
channel, and the Policy Guardrail has already approved that exact decision.

You MUST obey the approved action and channel exactly.
You MUST NOT change them.
You MUST NOT create a different strategy.
You MUST NOT select a different channel.
You MUST NOT invent customer data.
You MUST NOT invent a payment link.
You MUST NOT claim an action succeeded unless the tool reports success.

The application provides only the tool that is permitted for this exact
approved action/channel combination.

Your job:
1. Call the single provided execution tool exactly once.
2. Do not call any other tool.
3. Do not perform a second action.
4. Report the tool result concisely.

The tool performs the real external operation where supported.
"""


# --------------------------------------------------
# Build Executor Agent
# --------------------------------------------------


def build_recovery_executor(tools: list[Callable]) -> Agent:
    """Build the Groq-backed Executor Agent with only approved tools."""

    return Agent(
        model=groq_model,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
    )


# --------------------------------------------------
# Execute approved decision
# --------------------------------------------------


def execute_strategy(
    context,
    decision: RecoveryDecisionRecord,
    attempt: RecoveryAttempt,
    db,
) -> ExecutionResult:
    """
    Execute the persisted and guardrail-approved decision using a Groq-backed
    Strands Executor Agent.

    The LLM may choose/call the provided execution tool, but the application
    decides which tool is available. Therefore the Executor Agent cannot
    override the action/channel approved by the Strategist + guardrail.
    """

    action = decision.action
    channel = decision.channel

    if action not in SUPPORTED_ACTIONS:
        raise ValueError(
            f"Unsupported recovery action: {action}"
        )

    if channel not in SUPPORTED_CHANNELS:
        raise ValueError(
            f"Unsupported recovery channel: {channel}"
        )

    if attempt.action != action or attempt.channel != channel:
        raise ValueError(
            "Attempt does not match persisted decision. "
            f"attempt_id={attempt.id}"
        )

    # Reset per-invocation tool result state.
    execution_state["result"] = None

    # --------------------------------------------------
    # Deterministically choose the ONLY legal tool.
    # --------------------------------------------------

    if action == "no_action":
        if channel != "none":
            raise ValueError(
                "no_action must use channel='none'."
            )

        tools = [
            _make_tool(
                name="no_action",
                description=(
                    "Record that no recovery action should be taken. "
                    "Call exactly once."
                ),
                handler=lambda: _execute_no_action(
                    attempt,
                    decision,
                ),
            )
        ]

    elif action == "contact_support":
        if channel != "none":
            raise ValueError(
                "contact_support must use channel='none'."
            )

        tools = [
            _make_tool(
                name="contact_support",
                description=(
                    "Create an internal support escalation for this recovery "
                    "attempt. Call exactly once."
                ),
                handler=lambda: _execute_support(
                    attempt,
                    decision,
                ),
            )
        ]

    elif action in {
        "send_payment_link",
        "retry_payment",
    }:
        if channel not in SUPPORTED_REAL_PAYMENT_LINK_CHANNELS:
            raise ValueError(
                "Real Payment Link execution currently supports "
                "email and sms only. "
                f"Received channel={channel}."
            )

        customer = _get_customer(
            attempt,
            db,
        )

        tools = [
            _make_tool(
                name=(
                    "send_payment_link_email"
                    if channel == "email"
                    else "send_payment_link_sms"
                ),
                description=(
                    "Create or reuse the Razorpay Payment Link for this "
                    "recovery attempt and notify the customer through the "
                    f"approved {channel} channel. Call exactly once."
                ),
                handler=lambda: _create_or_reuse_payment_link(
                    attempt,
                    decision,
                    customer,
                    db,
                ),
            )
        ]

    elif action == "send_reminder":
        if channel not in SUPPORTED_REAL_PAYMENT_LINK_CHANNELS:
            raise ValueError(
                "Real reminder execution currently supports email and sms only. "
                f"Received channel={channel}."
            )

        tools = [
            _make_tool(
                name=(
                    "send_payment_link_reminder_email"
                    if channel == "email"
                    else "send_payment_link_reminder_sms"
                ),
                description=(
                    "Send a reminder for the existing Razorpay recovery "
                    "Payment Link through the approved channel. Call exactly once."
                ),
                handler=lambda: _execute_reminder(
                    attempt,
                    decision,
                    db,
                ),
            )
        ]

    else:
        raise ValueError(
            f"No Executor implementation for action={action} "
            f"channel={channel}"
        )

    decision_data = {
        "attempt_id": attempt.id,
        "case_id": attempt.case_id,
        "decision_id": decision.id,
        "action": decision.action,
        "channel": decision.channel,
        "reason": decision.reason,
        "message": decision.message,
        "confidence": float(decision.confidence),
        "priority": decision.priority,
    }

    prompt = f"""
Execute the already approved recovery decision below.

APPROVED EXECUTION:
{json.dumps(decision_data, separators=(",", ":"))}

EXECUTION RULES:
- Call the single provided tool exactly once.
- The provided tool is the ONLY permitted execution capability.
- Do not change the action.
- Do not change the channel.
- Do not invent customer data.
- Do not invent external IDs or payment links.
- Do not call another tool.
- Report the tool result concisely.
"""

    executor = build_recovery_executor(tools)
    executor(prompt)

    result = execution_state.get("result")

    if result is None:
        raise RuntimeError(
            "Executor Agent returned without invoking its execution tool."
        )

    if not result.success:
        raise RuntimeError(
            result.error
            or "Executor tool reported execution failure."
        )

    return result
