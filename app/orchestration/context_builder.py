"""Context builder for scoped assistant runtime state."""

from app.models.session import SessionContext


class ContextBuilder:
    """Build minimal runtime context from validated server-side state."""

    def build(self, session: SessionContext) -> dict:
        """Return safe context that does not invent business data."""
        return {
            "session_id": session.session_id,
            "customer_id": session.principal.customer_id,
            "manufacturer_id": session.principal.manufacturer_id,
            "permissions": session.principal.permissions,
        }
