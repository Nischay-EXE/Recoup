from app.db.database import SessionLocal
from app.state.context_service import build_recovery_context
from app.agent.analyst_agent import build_recovery_analyst


db = SessionLocal()

try:
    context = build_recovery_context("evt_test_007", db)

    print("\n===== RECOVERY CONTEXT =====")
    print(context.model_dump())

    analyst = build_recovery_analyst()

    prompt = f"""
Analyze the following verified recovery context.

Recovery Context:
{context.model_dump()}

Return the result as an AnalystReport.
"""

    result = analyst(prompt)

    print("\n===== ANALYST RESULT =====")
    print(result)

finally:
    db.close()
