"""Structured logging setup for the service."""

import logging
import sys

from pythonjsonlogger import jsonlogger


def configure_logging(level: str, service_name: str) -> None:
    """Configure JSON logs with service metadata."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(service)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(ServiceNameFilter(service_name))
    root_logger.addHandler(handler)


class ServiceNameFilter(logging.Filter):
    """Attach static service metadata to every log record."""

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:
        record.service = self.service_name
        return True
