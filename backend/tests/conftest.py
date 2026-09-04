"""Test defaults that allow the suite to run without real API credentials."""

import os
from pathlib import Path

from dotenv import load_dotenv


# Load the developer's local backend/.env when it exists.
# The file is gitignored and is never committed.
BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


# Keep external API credentials safe for tests.
# These are only used when the real values are not already configured.
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("RAZORPAY_KEY_ID", "test-key-id")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "test-key-secret")
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "test-webhook-secret")