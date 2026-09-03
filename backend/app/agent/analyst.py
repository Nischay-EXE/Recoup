from decimal import Decimal
from pydantic import BaseModel, Field


class AnalystReport(BaseModel):
    """
    Structured analysis produced by the Recovery Analyst.

    The analyst evaluates the payment situation and customer context.
    It does NOT choose the final recovery action.
    """

    event_id: str

    situation: str = Field(
        description="Concise description of what happened with the payment."
    )

    payment_risk: str = Field(
        description="Assessment of payment recovery risk: low, medium, or high."
    )

    customer_profile: str = Field(
        description="Relevant interpretation of the customer's payment history."
    )

    recovery_history: str = Field(
        description="Interpretation of previous recovery attempts."
    )

    key_factors: list[str] = Field(
        default_factory=list,
        description="Important facts that should influence the recovery strategy."
    )

    recommended_considerations: list[str] = Field(
        default_factory=list,
        description="Things the strategist should consider when choosing a recovery action."
    )