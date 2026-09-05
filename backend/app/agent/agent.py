import json

from strands import Agent
from strands.models.openai import OpenAIModel

from app.agent.schema import AgentDecision
from app.config import settings
from app.state.context import RecoveryContext


# --------------------------------------------------
# Configuration
# --------------------------------------------------

MODEL_ID = "qwen/qwen3.6-27b"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


# --------------------------------------------------
# Agent Instructions
# --------------------------------------------------

SYSTEM_PROMPT = """
You are the Revenue Recovery Decision Agent.

Your job is to propose the best recovery decision for a payment recovery
case using a verified RecoveryContext.

You are a decision-making agent, but you are NOT an execution agent.

IMPORTANT RULES:

1. Use only facts present in the provided RecoveryContext.
2. Do not invent customer history, payment history, failure reasons,
   previous attempts, or merchant policies.
3. Consider the customer's payment history.
4. Consider previous recovery attempts.
5. Consider payment amount and payment status.
6. Consider merchant policy when available.
7. Select the most appropriate recovery action.
8. Select the most appropriate communication channel.
9. Provide a concise reason for the recommendation.
10. Provide confidence between 0.0 and 1.0.
11. Assign an appropriate priority.
12. Do not execute the recovery action.
13. Do not claim that money was recovered unless the context explicitly
    contains evidence of recovery.
14. Do not provide chain-of-thought reasoning.

Possible recovery actions:

- send_payment_link
- contact_support
- no_action

Possible communication channels:

- whatsapp
- email
- phone_call
- support
- none

The architecture is:

RecoveryContext
    -> Analyst
    -> AnalystReport
    -> Strategist / Decision Agent
    -> AgentDecision
    -> Merchant Policy
    -> Final Decision
    -> Executor

Your output is only the proposed AgentDecision.
"""


# --------------------------------------------------
# Groq Model through Strands
# --------------------------------------------------

groq_model = OpenAIModel(
    client_args={
        "api_key": settings.groq_api_key,
        "base_url": GROQ_BASE_URL,
    },
    model_id=MODEL_ID,
    params={
        "temperature": 0.1,
        "max_tokens": 600,
        "reasoning_effort": "none",
    },
)


# --------------------------------------------------
# Recovery Decision Agent
# --------------------------------------------------

recovery_agent = Agent(
    model=groq_model,
    system_prompt=SYSTEM_PROMPT,
)


# --------------------------------------------------
# Decision Function
# --------------------------------------------------

def propose_recovery_decision(
    context: RecoveryContext,
) -> AgentDecision:
    """
    Ask the Recovery Decision Agent to propose a recovery decision
    from a verified RecoveryContext.
    """

    context_json = json.dumps(
        context.model_dump(mode="json"),
        indent=2,
    )

    prompt = f"""
Analyze this verified payment recovery context and propose the best
recovery decision.

RECOVERY CONTEXT:
{context_json}

Determine:

- recovery action
- communication channel
- concise reason
- confidence from 0.0 to 1.0
- priority

Use only the verified information provided.

Do not execute anything.
Return only the structured AgentDecision.
"""

    result = recovery_agent(
        prompt,
        structured_output_model=AgentDecision,
    )

    return result.structured_output
