from app.db.database import SessionLocal
from app.state.context_service import build_recovery_context
from app.agent.strategist_agent import build_recovery_strategist

TEST_EVENT_ID = "evt_test_007"
db = SessionLocal()

try:
    context = build_recovery_context(TEST_EVENT_ID, db)

    print("\n===== RECOVERY CONTEXT =====")
    print(context.model_dump())

    strategist = build_recovery_strategist()

    prompt = f"""
You are the Recovery Strategist.

Using the verified RecoveryContext below, determine the most appropriate
recovery strategy.

Recovery Context:
{context.model_dump()}

Return only the structured strategist decision.
Do not execute any action.
"""

    result = strategist(prompt)

    print("\n===== STRATEGIST RESULT =====")
    print(result)

finally:
    db.close()
