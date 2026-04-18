import json
import logging

from backend.core.logging import JsonFormatter, log_event


def test_json_formatter_renders_structured_event():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="",
        args=(),
        exc_info=None,
    )
    record.event = "strava_webhook_received"
    record.owner_id = 123

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["service"] == "human-engine-backend"
    assert payload["event"] == "strava_webhook_received"
    assert payload["owner_id"] == 123
    assert "timestamp" in payload
    assert "message" not in payload


def test_log_event_emits_json_payload():
    messages: list[str] = []
    logger = logging.getLogger("test_structured_logging")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.emit = lambda record: messages.append(handler.format(record))
    logger.addHandler(handler)

    log_event(
        logger,
        "healthkit_full_sync_started",
        user_id="user-1",
        counts={"sleep": 2, "hrv": 3, "rhr": 1},
    )

    payload = json.loads(messages[0])

    assert payload["event"] == "healthkit_full_sync_started"
    assert payload["user_id"] == "user-1"
    assert payload["counts"] == {"sleep": 2, "hrv": 3, "rhr": 1}
