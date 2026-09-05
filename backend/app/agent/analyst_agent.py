import json
import os

from dotenv import load_dotenv
from strands import Agent
from strands.models.openai import OpenAIModel
from pydantic import BaseModel, Field, field_validator

from app.agent.schema import AnalystReport
from app.state.context import RecoveryContext


class _AnalystReportWire(BaseModel):
    """Provider-facing schema tolerant of common JSON serialization drift."""

    failure_analysis: str = ""
    customer_analysis: str = ""
    # Groq/Strands structured tool schemas are more reliable with scalar
    # fields. Keep these provider-facing values as JSON-encoded strings and
    # normalize them into real lists at the application boundary.
    recovery_factors: str | None = ""
    risk_level: str = "medium"
    considerations: str | None = ""

    @field_validator("recovery_factors", "considerations", mode="before")
    @classmethod
    def normalize_list_wire_value(cls, value):
        """Accept provider arrays but expose a scalar JSON string schema."""
        if value is None:
            return ""
        if isinstance(value, list):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    @field_validator("risk_level", mode="before")
    @classmethod
    def normalize_risk_level(cls, value):
        value = str(value or "medium").strip().lower()
        return value if value in {"low", "medium", "high"} else "medium"


def _normalize_string_list(value) -> list[str]:
    """Normalize provider output such as a single string into a real list."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        return [text]
    return [str(value).strip()] if str(value).strip() else []


def _to_analyst_report(raw) -> AnalystReport:
    """Convert tolerant provider output into the strict application model."""
    data = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw)
    return AnalystReport(
        failure_analysis=str(data.get("failure_analysis") or ""),
        customer_analysis=str(data.get("customer_analysis") or ""),
        recovery_factors=_normalize_string_list(data.get("recovery_factors")),
        risk_level=str(data.get("risk_level") or "medium").lower(),
        considerations=_normalize_string_list(data.get("considerations")),
    )


# --------------------------------------------------
# Environment
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# Configuration
# --------------------------------------------------

MODEL_ID = "qwen/qwen3.6-27b"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is not configured in the environment."
    )


# --------------------------------------------------
# Analyst Instructions
# --------------------------------------------------

SYSTEM_PROMPT = """
You are the Recovery Analyst in a payment recovery system.

Analyze a verified RecoveryContext and return a concise structured
AnalystReport for the Recovery Strategist.

Your responsibilities:
1. Identify the payment failure or risk situation.
2. Summarize relevant customer payment history.
3. Summarize previous recovery attempts.
4. Identify important recovery factors.
5. Assess risk as low, medium, or high.
6. Provide brief considerations for the Recovery Strategist.

STRICT RULES:
- Use only facts present in the RecoveryContext.
- Never invent customer information, payment history, failure reasons,
  recovery attempts, or merchant policies.
- Do not claim a payment was recovered unless the context explicitly
  shows recovery.
- Do not choose the final recovery action.
- Do not choose the communication channel.
- Do not execute anything.
- Do not repeat the entire RecoveryContext.
- Keep every field concise and factual.
- Do not provide chain-of-thought or reasoning.

STRUCTURED OUTPUT REQUIREMENTS:
- recovery_factors MUST be a JSON-encoded string containing an array of strings.
  Example: "[\"factor one\",\"factor two\"]"
- considerations MUST be a JSON-encoded string containing an array of strings.
  Example: "[\"consideration one\"]"
- Do not return recovery_factors or considerations as a native array in the
  JSON response; encode the array as a JSON string.
- If there are no relevant factors, return "[]".
- If there are no relevant considerations, return "[]".
- risk_level MUST be exactly one of: "low", "medium", "high".

The expected conceptual shape is:

{
  "failure_analysis": "brief factual failure/risk analysis",
  "customer_analysis": "brief factual customer-history analysis",
  "recovery_factors": "[\"factor one\",\"factor two\"]",
  "risk_level": "medium",
  "considerations": "[\"consideration one\",\"consideration two\"]"
}

Return only the JSON AnalystReport object.
"""


# --------------------------------------------------
# Groq Model through Strands
# --------------------------------------------------

groq_model = OpenAIModel(
    client_args={
        "api_key": GROQ_API_KEY,
        "base_url": GROQ_BASE_URL,
    },
    model_id=MODEL_ID,
    params={
        "temperature": 0.2,
        "max_tokens": 1000,
        "reasoning_effort": "none",
    },
)


# --------------------------------------------------
# Strands Analyst
# --------------------------------------------------

def build_recovery_analyst() -> Agent:
    """
    Build and return the Recovery Analyst agent.
    """

    return Agent(
        model=groq_model,
        system_prompt=SYSTEM_PROMPT,
    )


# --------------------------------------------------
# Compact Analyst Context
# --------------------------------------------------

def _build_compact_context(
    context: RecoveryContext,
) -> dict:
    """
    Build a bounded representation of RecoveryContext for the LLM.

    The complete RecoveryContext remains available for audit/history.
    Only decision-relevant fields are sent to the Analyst.
    """

    current_payment = {
        "payment_id": context.payment_id,
        "order_id": context.order_id,
        "amount": (
            str(context.amount)
            if context.amount is not None
            else None
        ),
        "currency": context.currency,
        "status": context.payment_status,
    }

    customer_summary = {
        "customer_id": context.customer_id,
        "total_payments": context.customer_total_payments,
        "successful_payments": context.customer_successful_payments,
        "failed_payments": context.customer_failed_payments,
    }

    recent_payment_history = [
        {
            "payment_id": item.get("payment_id"),
            "amount": item.get("amount"),
            "currency": item.get("currency"),
            "status": item.get("status"),
            "failure_reason": item.get("failure_reason"),
            "created_at": item.get("created_at"),
        }
        for item in (context.payment_history or [])[-5:]
    ]

    recent_recovery_attempts = [
        {
            "attempt_number": item.get("attempt_number"),
            "action": item.get("action"),
            "channel": item.get("channel"),
            "status": item.get("status"),
            "amount_at_risk": item.get("amount_at_risk"),
            "amount_recovered": item.get("amount_recovered"),
        }
        for item in (context.previous_recovery_attempts or [])[-5:]
    ]

    return {
        "event": {
            "event_id": context.event_id,
            "event_type": context.event_type,
            "revenue_object_type": getattr(
                context,
                "revenue_object_type",
                None,
            ),
        },
        "case": {
            "case_id": getattr(
                context,
                "case_id",
                None,
            ),
            "current_attempt": getattr(
                context,
                "current_case_attempt",
                0,
            ),
        },
        "current_payment": current_payment,
        "customer": customer_summary,
        "recent_payment_history": recent_payment_history,
        "previous_attempt_count": context.previous_attempts,
        "recent_recovery_attempts": recent_recovery_attempts,
        "merchant_policy": context.merchant_policy or {},
    }


# --------------------------------------------------
# Prompt
# --------------------------------------------------

def _build_analysis_prompt(
    context_json: str,
    retry: bool = False,
) -> str:
    """
    Build the Analyst prompt.

    retry=True is used only after a structured-output validation failure.
    """

    retry_instruction = ""

    if retry:
        retry_instruction = """
IMPORTANT CORRECTION:
The previous response failed structured-output validation.

You MUST follow the field types exactly.

In particular:

recovery_factors = JSON-ENCODED ARRAY STRING
Example:
"[\"failed payment\",\"previous successful payment\"]"

considerations = JSON-ENCODED ARRAY STRING
Example:
"[\"A payment retry may be appropriate\"]"

Return the structured AnalystReport only.
"""

    return f"""
Analyze this verified recovery context.

{retry_instruction}

Return a concise AnalystReport for the Recovery Strategist.

Focus on:
1. The current payment/revenue risk.
2. Relevant customer history.
3. Previous recovery attempts.
4. Important recovery factors.
5. Overall risk: low, medium, or high.
6. Brief considerations for the Strategist.

STRICT OUTPUT RULES:
- Use only facts provided.
- Do not invent information.
- Do not choose an action.
- Do not choose a communication channel.
- Do not execute anything.
- Do not claim recovery without evidence.
- Keep every field concise.
- Do not provide chain-of-thought.

FIELD TYPES:
- failure_analysis: string
- customer_analysis: string
- recovery_factors: JSON-encoded array string
- risk_level: one of "low", "medium", "high"
- considerations: JSON-encoded array string

Examples:
recovery_factors: "[\"The current payment failed\",\"Customer has previous successful payments\"]"
considerations: "[\"A recovery intervention may be appropriate\"]"

If there are no items, return "[]".

Return only the JSON AnalystReport object.

VERIFIED RECOVERY CONTEXT:
{context_json}
"""


# --------------------------------------------------
# Analysis Function
# --------------------------------------------------

def _extract_analyst_payload(result) -> dict:
    """Extract and validate a JSON object from a plain Strands Agent result.

    We intentionally do not use ``structured_output_model`` here. Strands
    implements structured output as a generated tool specification, and the
    Groq model used by this project has repeatedly returned native arrays for
    fields that the generated schema declared as strings. That failure occurs
    before our Pydantic validators can normalize the value.
    """
    text = str(result).strip()
    if not text:
        raise ValueError("Analyst returned an empty response.")

    # Remove common markdown fencing without requiring the model to use it.
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        # Be tolerant if the model adds a short prefix/suffix around the JSON.
        decoder = json.JSONDecoder()
        payload = None
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                candidate, _ = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                payload = candidate
                break
        if payload is None:
            raise ValueError("Analyst response was not valid JSON.")

    if not isinstance(payload, dict):
        raise ValueError("Analyst response must be a JSON object.")

    return payload


def analyze_recovery_context(
    context: RecoveryContext,
) -> AnalystReport:
    """Analyze a verified RecoveryContext with plain JSON output.

    The provider response is parsed locally and then validated against the
    application's strict ``AnalystReport`` model. This keeps provider output
    drift outside the business-state contract while avoiding the Strands
    structured-output tool/schema path that has been rejecting native arrays.
    """
    compact_context = _build_compact_context(context)
    context_json = json.dumps(compact_context, separators=(",", ":"))
    analyst = build_recovery_analyst()

    for retry in (False, True):
        prompt = _build_analysis_prompt(
            context_json=context_json,
            retry=retry,
        )
        try:
            result = analyst(prompt)
            payload = _extract_analyst_payload(result)
            return _to_analyst_report(payload)
        except Exception as exc:
            if not retry:
                print(
                    "[ANALYST] Plain JSON output parsing/validation failed; "
                    "retrying once with strict JSON instructions. "
                    f"error={exc}"
                )
                continue
            raise

    raise RuntimeError("Analyst analysis failed unexpectedly.")
