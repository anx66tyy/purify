from __future__ import annotations


class LoggingService:
    def __init__(self, bot) -> None:
        self.bot = bot

    async def log_event(self, guild, event_type: str, payload: dict | None = None) -> None:
        return None
