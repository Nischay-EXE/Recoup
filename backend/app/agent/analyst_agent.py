import json
import os

from dotenv import load_dotenv
from strands import Agent
from strands.models.openai import OpenAIModel

from app.agent.schema import AnalystReport
from app.state.context import RecoveryContext


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
- recovery_factors MUST be an array/list of strings.
- considerations MUST be an array/list of strings.
- NEVER return recovery_factors as a single string.
- NEVER return considerations as a single string.
- If there is only one factor, return ["that factor"].
- If there is only one consideration, return ["that consideration"].
- If there are no relevant factors, return [].
- If there are no relevant considerations, return [].
- risk_level MUST be exactly one of: "low", "medium", "high".

The expected conceptual shape is:

{
  "summary": "brief factual summary",
  "recovery_factors": [
    "factor one",
    "factor two"
  ],
  "risk_level": "medium",
  "considerations": [
    "consideration one",
    "consideration two"
  ]
}

Return only the structured AnalystReport.
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

recovery_factors = ARRAY OF STRINGS
Example:
["failed payment", "previous successful payment"]

NOT:
"failed payment"

considerations = ARRAY OF STRINGS
Example:
["A payment retry may be appropriate"]

NOT:
"A payment retry may be appropriate"

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
- summary: string
- recovery_factors: ARRAY OF STRINGS
- risk_level: one of "low", "medium", "high"
- considerations: ARRAY OF STRINGS

Examples of VALID array values:

recovery_factors:
[
  "The current payment failed",
  "Customer has previous successful payments"
]

considerations:
[
  "A recovery intervention may be appropriate"
]

If only one item exists, it is STILL an array:

recovery_factors:
[
  "The current payment failed"
]

Never produce:

recovery_factors:
"The current payment failed"

Never produce:

considerations:
"A recovery intervention may be appropriate"

Return only the structured AnalystReport.

VERIFIED RECOVERY CONTEXT:
{context_json}
"""


# --------------------------------------------------
# Analysis Function
# --------------------------------------------------

def analyze_recovery_context(
    context: RecoveryContext,
) -> AnalystReport:
    """
    Analyze a verified RecoveryContext using a compact,
    decision-relevant representation.

    The full RecoveryContext remains intact for audit/history.
    Only the LLM input is intentionally bounded.

    A single retry is performed if the model produces structured output
    that fails the AnalystReport schema validation.
    """

    compact_context = _build_compact_context(context)

    context_json = json.dumps(
        compact_context,
        separators=(",", ":"),
    )

    analyst = build_recovery_analyst()

    prompt = _build_analysis_prompt(
        context_json=context_json,
        retry=False,
    )

    try:
        result = analyst(
            prompt,
            structured_output_model=AnalystReport,
        )

        return result.structured_output

    except Exception as first_error:
        print(
            "[ANALYST] Structured output validation failed; "
            "retrying once with strict array instructions. "
            f"error={first_error}"
        )

        retry_prompt = _build_analysis_prompt(
            context_json=context_json,
            retry=True,
        )

        result = analyst(
            retry_prompt,
            structured_output_model=AnalystReport,
        )

        return result.structured_output