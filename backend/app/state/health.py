from __future__ import annotations

import os
import socket
import time
from datetime import datetime, timezone

from sqlalchemy import text

from app.db.database import engine
from app.queue.redis import redis_client

WORKER_HEARTBEAT_KEY_PREFIX = "recovery:health:worker:"
SCHEDULER_HEARTBEAT_KEY = "recovery:health:scheduler"
WORKER_STALE_AFTER_SECONDS = 60
SCHEDULER_STALE_AFTER_SECONDS = 90


def _iso_from_epoch(value: str | bytes | None) -> str | None:
    if value is None:
        return None
    try:
        timestamp = float(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    ).isoformat()


def touch_worker_heartbeat(worker_name: str) -> None:
    redis_client.set(
        f"{WORKER_HEARTBEAT_KEY_PREFIX}{worker_name}",
        str(time.time()),
        ex=WORKER_STALE_AFTER_SECONDS * 2,
    )


def touch_scheduler_heartbeat() -> None:
    redis_client.set(
        SCHEDULER_HEARTBEAT_KEY,
        str(time.time()),
        ex=SCHEDULER_STALE_AFTER_SECONDS * 2,
    )


def _worker_health() -> dict:
    worker_name = os.getenv("WORKER_NAME", socket.gethostname())
    key = f"{WORKER_HEARTBEAT_KEY_PREFIX}{worker_name}"
    raw = redis_client.get(key)

    if raw is None:
        return {
            "status": "unavailable",
            "last_heartbeat": None,
            "detail": "Recovery worker heartbeat has not been observed.",
        }

    try:
        age = max(0.0, time.time() - float(raw))
    except (TypeError, ValueError):
        return {
            "status": "unavailable",
            "last_heartbeat": None,
            "detail": "Recovery worker heartbeat value is invalid.",
        }

    healthy = age <= WORKER_STALE_AFTER_SECONDS

    return {
        "status": "healthy" if healthy else "unavailable",
        "last_heartbeat": _iso_from_epoch(raw),
        "age_seconds": round(age, 1),
        "detail": (
            "Recovery worker heartbeat is current."
            if healthy
            else "Recovery worker heartbeat is stale."
        ),
    }


def _scheduler_health() -> dict:
    raw = redis_client.get(SCHEDULER_HEARTBEAT_KEY)

    if raw is None:
        return {
            "status": "unavailable",
            "last_heartbeat": None,
            "detail": "Recovery scheduler heartbeat has not been observed.",
        }

    try:
        age = max(0.0, time.time() - float(raw))
    except (TypeError, ValueError):
        return {
            "status": "unavailable",
            "last_heartbeat": None,
            "detail": "Recovery scheduler heartbeat value is invalid.",
        }

    healthy = age <= SCHEDULER_STALE_AFTER_SECONDS

    return {
        "status": "healthy" if healthy else "unavailable",
        "last_heartbeat": _iso_from_epoch(raw),
        "age_seconds": round(age, 1),
        "detail": (
            "Recovery scheduler heartbeat is current."
            if healthy
            else "Recovery scheduler heartbeat is stale."
        ),
    }


def _database_health() -> dict:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "detail": "PostgreSQL connectivity verified with SELECT 1.",
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "detail": f"PostgreSQL probe failed: {type(exc).__name__}.",
        }


def _redis_health() -> dict:
    try:
        redis_client.ping()
        return {
            "status": "healthy",
            "detail": "Redis connectivity verified with PING.",
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "detail": f"Redis probe failed: {type(exc).__name__}.",
        }


def _provider_health() -> dict:
    from app.config import settings

    configured = bool(
        settings.razorpay_key_id
        and settings.razorpay_key_secret
    )

    return {
        "status": "configured" if configured else "unavailable",
        "detail": (
            "Razorpay credentials are configured; external provider reachability "
            "is intentionally not probed by /health."
            if configured
            else "Razorpay credentials are not configured."
        ),
    }


def get_system_health() -> dict:
    """Return real runtime probes without claiming unverified health."""

    redis_status = _redis_health()

    if redis_status["status"] != "healthy":
        worker_status = {
            "status": "unavailable",
            "detail": "Worker heartbeat cannot be checked while Redis is unavailable.",
        }
        scheduler_status = {
            "status": "unavailable",
            "detail": "Scheduler heartbeat cannot be checked while Redis is unavailable.",
        }
    else:
        worker_status = _worker_health()
        scheduler_status = _scheduler_health()

    database_status = _database_health()
    provider_status = _provider_health()

    components = {
        "api": {"status": "healthy", "detail": "FastAPI /health is responding."},
        "redis": redis_status,
        "database": database_status,
        "worker": worker_status,
        "scheduler": scheduler_status,
        "razorpay": provider_status,
    }

    required_statuses = [
        components[name]["status"]
        for name in ("api", "redis", "database", "worker", "scheduler")
    ]

    overall = (
        "healthy"
        if all(status == "healthy" for status in required_statuses)
        else "degraded"
    )

    return {
        "status": overall,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "components": components,
    }
