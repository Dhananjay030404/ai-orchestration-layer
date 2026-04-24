"""Structured logging setup for the service."""

import logging
import sys
from collections.abc import MutableMapping
from datetime import datetime, timezone
from typing import Any

from pythonjsonlogger import jsonlogger


def configure_logging(level: str, service_name: str) -> None:
    """Configure production-friendly JSON logs with service metadata."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonLogFormatter("%(timestamp)s %(level)s %(name)s %(message)s %(service)s")
    handler.setFormatter(formatter)
    handler.addFilter(ServiceNameFilter(service_name))
    root_logger.addHandler(handler)

    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.error").handlers.clear()


class ServiceNameFilter(logging.Filter):
    """Attach static service metadata to every log record."""

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:
        record.service = self.service_name
        return True


class JsonLogFormatter(jsonlogger.JsonFormatter):
    """Small formatter that keeps the log shape stable and extensible."""

    def add_fields(
        self,
        log_record: MutableMapping[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name

        log_record.setdefault("correlationId", None)
        log_record.setdefault("sessionId", None)
        log_record.setdefault("customerId", None)
