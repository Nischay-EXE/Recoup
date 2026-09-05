from app.db.database import SessionLocal
from app.state.context_service import build_recovery_context

EVENT_IDS = [
    "evt_test_001",
    "evt_test_002",
    "evt_pipeline_001",
    "evt_pipeline_003",
    "evt_test_003",
    "evt_test_004",
    "evt_test_005",
    "evt_test_006",
    "evt_test_007",
]

db = SessionLocal()

try:
    for event_id in EVENT_IDS:
        print(f"\n===== {event_id} =====")

        try:
            context = build_recovery_context(event_id, db)
            print("NORMALIZED: YES")
            print(context.model_dump())

        except Exception as e:
            print("NORMALIZED: NO")
            print(f"ERROR: {e}")

finally:
    db.close()
