"""HTTP client boundary for VAM backend APIs."""

from typing import Any

from app.core.config import Settings, get_settings
from app.core.exceptions import ExternalServiceError


class VamClient:
    """Client for VAM internal APIs.

    TODO: Implement typed backend calls once endpoint contracts are finalized.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def request(
        self,
        method: str,
        path: str,
        *,
        token: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Placeholder for authenticated VAM backend calls.

        TODO: Implement this with httpx after endpoint contracts, retry policy,
        timeout policy, and audit requirements are finalized.
        """
        _ = (method, path, token, json)
        raise ExternalServiceError("vam-backend", "VAM backend integration is not implemented yet.")
