"""Safe test defaults; real credentials are never required by unit tests."""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/revenue_recovery")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("RAZORPAY_KEY_ID", "test-key-id")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "test-key-secret")
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "test-webhook-secret")
