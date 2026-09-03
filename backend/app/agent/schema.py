from pydantic import BaseModel, Field


class AgentDecision(BaseModel):
    """
    Structured decision produced by the AI recovery agent.
    """

    action: str = Field(
        description="The recovery action the agent recommends."
    )

    channel: str = Field(
        description="The communication channel for the recommended action."
    )

    reason: str = Field(
        description="Why the agent believes this is the best recovery strategy."
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="The agent's confidence in its recommendation."
    )

    priority: str = Field(
        description="How urgently the recovery case should be handled."
    )

class AnalystReport(BaseModel):
    """
    Structured analysis produced by the Recovery Analyst.
    """

    failure_analysis: str = Field(
        description="Analysis of why the payment failed or became at risk."
    )

    customer_analysis: str = Field(
        description="Relevant analysis of the customer's payment history."
    )

    recovery_factors: list[str] = Field(
        description="Important factors that may influence recovery."
    )

    risk_level: str = Field(
        description="Overall recovery risk: low, medium, or high."
    )

    considerations: list[str] = Field(
        description="Important considerations that the Strategist should evaluate."
    )