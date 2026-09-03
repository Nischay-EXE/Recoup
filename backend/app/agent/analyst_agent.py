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
- Return only the structured AnalystReport.

The Strategist will use your report to decide the recovery action.
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
        # Qwen 3.6 supports non-thinking mode on Groq.
        # This prevents reasoning tokens from consuming the output budget.
        "reasoning_effort": "none",
        #"reasoning_format": "hidden",
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
# Analysis Function
# --------------------------------------------------

def analyze_recovery_context(
    context: RecoveryContext,
) -> AnalystReport:
    """
    Analyze a verified RecoveryContext and return a structured AnalystReport.
    """

    context_json = json.dumps(
        context.model_dump(mode="json"),
        indent=2,
    )

    prompt = f"""
Analyze this verified payment recovery context.

Return a concise AnalystReport. Keep each field short.

Analyze only:
1. Payment failure / risk situation
2. Relevant customer history
3. Previous recovery attempts
4. Important recovery factors
5. Overall risk level: low, medium, or high
6. Considerations for the Recovery Strategist

Do NOT choose a recovery action.
Do NOT choose a communication channel.
Do NOT execute anything.
Do NOT repeat the entire context.
Do NOT provide chain-of-thought.

RECOVERY CONTEXT:
{context_json}

Return only the structured AnalystReport.
"""

    analyst = build_recovery_analyst()

    result = analyst(
        prompt,
        structured_output_model=AnalystReport,
    )

    return result.structured_output
