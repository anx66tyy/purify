from __future__ import annotations


class SecurityService:
    def __init__(self, bot) -> None:
        self.bot = bot

    async def handle_member_join(self, member) -> None:
        return None

    async def handle_message(self, message) -> None:
        return None
