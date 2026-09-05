import os
from typing import Any

import redis


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0",
)

STREAM_NAME = "recovery:events"


redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_timeout=None,
    socket_connect_timeout=5,
)


def publish_recovery_event(event_id: str) -> str:
    message_id = redis_client.xadd(
        STREAM_NAME,
        {
            "event_id": event_id,
        },
    )

    return message_id


def read_recovery_events(
    consumer_group: str,
    consumer_name: str,
    count: int = 1,
    block_ms: int = 5000,
) -> list[tuple[str, dict[str, Any]]]:

    messages = redis_client.xreadgroup(
        groupname=consumer_group,
        consumername=consumer_name,
        streams={STREAM_NAME: ">"},
        count=count,
        block=block_ms,
    )

    events: list[tuple[str, dict[str, Any]]] = []

    for _, stream_messages in messages:
        for message_id, data in stream_messages:
            events.append((message_id, data))

    return events


def claim_pending_recovery_events(
    consumer_group: str,
    consumer_name: str,
    min_idle_ms: int = 30_000,
    count: int = 1,
) -> list[tuple[str, dict[str, Any]]]:

    next_id, messages, _ = redis_client.xautoclaim(
        name=STREAM_NAME,
        groupname=consumer_group,
        consumername=consumer_name,
        min_idle_time=min_idle_ms,
        start_id="0-0",
        count=count,
    )

    events: list[tuple[str, dict[str, Any]]] = []

    for message_id, data in messages:
        events.append((message_id, data))

    return events


def acknowledge_recovery_event(
    consumer_group: str,
    message_id: str,
) -> int:

    return redis_client.xack(
        STREAM_NAME,
        consumer_group,
        message_id,
    )


def ensure_consumer_group(
    consumer_group: str,
) -> None:

    try:
        redis_client.xgroup_create(
            name=STREAM_NAME,
            groupname=consumer_group,
            id="0",
            mkstream=True,
        )

    except Exception as exc:
        if "BUSYGROUP" not in str(exc):
            raise

def touch_heartbeat(key: str, ttl_seconds: int = 180) -> None:
    """Write a short-lived liveness heartbeat to Redis."""
    import time

    redis_client.set(key, str(time.time()), ex=ttl_seconds)
