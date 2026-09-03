import json
import os

from dotenv import load_dotenv
from strands import Agent
from strands.models.openai import OpenAIModel

from app.agent.schema import AgentDecision, AnalystReport
from app.state.capabilities import get_execution_capabilities
from app.state.context import RecoveryContext


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
# Strategist instructions
# --------------------------------------------------

SYSTEM_PROMPT = """
You are the Recovery Strategist in a payment recovery system.

Your job is to use a verified RecoveryContext and an AnalystReport to
propose ONE appropriate recovery strategy.

The Analyst has already analyzed the situation.
Do not repeat the analysis.

Your responsibility is to decide:

- ONE action
- ONE communication channel
- priority
- confidence
- concise internal reason

IMPORTANT RULES:

1. Use only information provided in the RecoveryContext and AnalystReport.
2. Do not invent customer information.
3. Do not invent payment history.
4. Do not invent failure reasons.
5. Do not invent previous recovery attempts.
6. Do not claim money was recovered unless the context explicitly says so.
7. Do not execute anything.
8. Do not call external services.
9. Do not write a customer-facing message.
10. Do not provide chain-of-thought reasoning.
11. Return only the structured AgentDecision.
12. Choose exactly ONE action.
13. Choose exactly ONE channel.

EXECUTION CAPABILITIES:

The available execution capabilities are provided dynamically with each
strategy request.

You MUST treat those capabilities as the source of truth.

You may ONLY select an action + channel combination that is explicitly
available in the provided execution capabilities.

Do NOT assume that a channel is available.

For example, if:

send_payment_link -> ["email", "sms"]

then:

send_payment_link + email = valid
send_payment_link + sms = valid
send_payment_link + whatsapp = invalid

Do not select an unsupported combination even if the channel would otherwise
be a reasonable recovery option.

DECISION GUIDELINES:

- If the payment is already successful, choose no_action.
- If the event is not a payment failure, choose no_action.
- Consider the payment failure reason when available.
- Consider customer payment history when available.
- Consider previous recovery attempts across the entire recovery case.
- Treat current_case_attempt as the authoritative case-level attempt number.
- If prior attempts were actually executed, prefer a materially different
  recovery strategy when appropriate.
- Do not repeat the same action + channel combination when the case history
  shows it was already executed, unless the context provides a clear reason
  to retry it.
- A previous attempt with status "proposed" and no executed_at timestamp
  means the action has not yet been executed.
- Do NOT treat a "proposed" attempt as a completed customer contact.
- Do NOT treat a "proposed" attempt as a failed recovery attempt.
- If an appropriate recovery action is only "proposed" and has not been
  executed, the case may still require execution rather than no_action.
- Avoid repeating an action only when there is evidence that it was already
  executed or otherwise completed.
- Consider the amount at risk.
- Respect merchant policy information when provided.
- If there is insufficient basis for recovery, choose no_action.
- Use contact_support when the case clearly requires support intervention.
- Use retry_payment only when retrying the payment is appropriate.
- Use send_payment_link when a payment link is an appropriate recovery action.
- Use send_reminder when a reminder is appropriate.
- For later case attempts, escalate to contact_support when repeated recovery
  efforts have failed and support intervention is justified.

IMPORTANT:

The Strategist proposes a strategy.
It does NOT execute the strategy.

The Policy Guardrail will validate the strategy later.
The Executor will execute an approved strategy later.
"""


# --------------------------------------------------
# Build Strategist
# --------------------------------------------------

def build_recovery_strategist() -> Agent:
    """
    Build and return the Recovery Strategist agent.
    """

    return Agent(
        model=groq_model,
        system_prompt=SYSTEM_PROMPT,
    )


# --------------------------------------------------
# Generate Strategy
# --------------------------------------------------

def propose_strategy(
    context: RecoveryContext,
    analyst_report: AnalystReport,
) -> AgentDecision:
    """
    Generate a structured recovery strategy using the
    RecoveryContext, AnalystReport, and currently available
    execution capabilities.
    """

    context_json = json.dumps(
        context.model_dump(mode="json"),
        indent=2,
    )

    analyst_json = json.dumps(
        analyst_report.model_dump(mode="json"),
        indent=2,
    )

    capabilities = get_execution_capabilities()

    capabilities_json = json.dumps(
        capabilities,
        indent=2,
    )

    prompt = f"""
Create ONE recovery strategy using the verified information below.

AVAILABLE EXECUTION CAPABILITIES:
{capabilities_json}

IMPORTANT:

You MUST choose an action + channel combination that appears explicitly
inside AVAILABLE EXECUTION CAPABILITIES.

Do not invent or assume capabilities.

RECOVERY CONTEXT:
{context_json}

ANALYST REPORT:
{analyst_json}

Return only the structured AgentDecision.

The decision must contain:

- action
- channel
- reason
- confidence
- priority

The selected action and channel must be compatible with the available
execution capabilities.

Do not execute anything.
Do not create a customer-facing message.
Do not add additional fields.
Do not repeat the full analysis.
"""

    strategist = build_recovery_strategist()

    result = strategist(
        prompt,
        structured_output_model=AgentDecision,
    )

    return result.structured_output