"""Agent runtime orchestration boundary."""

from app.models.session import SessionContext


class AgentRuntime:
    """Coordinate conversation turns, context, tools, and formatted responses.

    TODO: Implement turn orchestration after conversation event contracts are finalized.
    """

    async def handle_turn(self, session: SessionContext, user_input: str) -> dict:
        """Placeholder for future conversation-turn orchestration."""
        return {
            "session_id": session.session_id,
            "status": "not_implemented",
            "input_received": bool(user_input),
        }
