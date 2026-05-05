"""Audit event recording boundary."""

import logging
from typing import Any


logger = logging.getLogger(__name__)


class AuditService:
    """Record security and assistant runtime events through the service log pipeline."""

    async def record_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Record an audit event without logging secrets or raw delegated tokens."""
        logger.info("audit_event", extra={"event_type": event_type, "payload_keys": list(payload)})
