from __future__ import annotations


class ModerationService:
    def __init__(self, bot) -> None:
        self.bot = bot

    async def log_action(self, guild, action: str, target, moderator=None, reason: str = "") -> None:
        return None
