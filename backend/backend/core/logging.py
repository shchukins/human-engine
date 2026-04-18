from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


SERVICE_NAME = "human-engine-backend"
_RESERVED_RECORD_FIELDS = set(logging.makeLogRecord({}).__dict__.keys())


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return str(value)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "service": getattr(record, "service", SERVICE_NAME),
        }

        event = getattr(record, "event", None)
        if event:
            payload["event"] = event

        message = record.getMessage()
        if message:
            payload["message"] = message

        for key, value in record.__dict__.items():
            if key in _RESERVED_RECORD_FIELDS or key.startswith("_"):
                continue
            if key in payload or value is None:
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=_json_default)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(level)


def log_event(logger: logging.Logger, event: str, **kwargs: Any) -> None:
    level = kwargs.pop("level", logging.INFO)
    message = kwargs.pop("message", "")
    extra = {
        "service": SERVICE_NAME,
        "event": event,
        **{key: value for key, value in kwargs.items() if value is not None},
    }
    logger.log(level, message, extra=extra)
