from unittest.mock import MagicMock, patch


def test_worker_heartbeat_is_unavailable_without_heartbeat():
    from app.state.health import _worker_health

    with patch("app.state.health.redis_client.get", return_value=None):
        result = _worker_health()

    assert result["status"] == "unavailable"
    assert result["last_heartbeat"] is None


def test_system_health_reports_worker_and_scheduler_from_real_heartbeats():
    from app.state import health

    now = health.time.time()
    redis = MagicMock()
    redis.ping.return_value = True
    redis.get.side_effect = [str(now), str(now)]

    with (
        patch.object(health, "redis_client", redis),
        patch.object(health.engine, "connect") as connect,
        patch("app.state.health._provider_health", return_value={"status": "configured", "detail": "ok"}),
        patch("app.state.health.os.getenv", return_value="test-worker"),
    ):
        connection = connect.return_value.__enter__.return_value
        response = health.get_system_health()

    connection.execute.assert_called_once()
    assert response["status"] == "healthy"
    assert response["components"]["worker"]["status"] == "healthy"
    assert response["components"]["scheduler"]["status"] == "healthy"
