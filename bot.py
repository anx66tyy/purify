from __future__ import annotations

import discord
from discord.ext import commands

from config import settings
from purify.core.database import Database
from purify.core.logger import logger


class PurifyBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.voice_states = True

        self.settings = settings
        self.db = Database(self.settings.database_url)
        self.logger = logger

        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,
            description="PURIFY - modular Discord bot",
        )

    async def get_prefix(self, bot: commands.Bot, message: discord.Message):
        if message.guild is None:
            return self.settings.prefix
        return [self.db.get_prefix(message.guild.id), self.settings.prefix]

    async def setup_hook(self) -> None:
        extensions = [
            "purify.cogs.utility",
            "purify.cogs.config",
            "purify.cogs.moderation",
            "purify.cogs.security",
            "purify.cogs.leveling",
            "purify.cogs.owner",
            "purify.cogs.music",
            "purify.cogs.voice",
            "purify.cogs.tickets",
            "purify.cogs.logging",
            "purify.cogs.notifications",
            "purify.cogs.errors",
        ]
        for extension in extensions:
            try:
                await self.load_extension(extension)
            except Exception:
                self.logger.exception("Failed to load extension %s", extension)
        await self.tree.sync()

    async def on_ready(self) -> None:
        self.logger.info("PURIFY ready. Guilds: %s", len(self.guilds))
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="/help | Protecting servers | /config",
            )
        )

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if message.guild:
            self.db.add_xp(message.guild.id, message.author.id, 5)
        await self.process_commands(message)


bot = PurifyBot()

if __name__ == "__main__":
    bot.run(settings.token)
