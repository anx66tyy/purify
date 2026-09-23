from __future__ import annotations


class NotificationService:
    def __init__(self, bot) -> None:
        self.bot = bot

    async def send_notification(self, guild, channel_id: int | None, text: str) -> None:
        return None
