from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Logging(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="loggingsetup")
    async def loggingsetup(self, interaction: discord.Interaction) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can configure logging.", ephemeral=True)
            return
        self.bot.db.set_setting(interaction.guild_id, "logging_enabled", True)
        await interaction.response.send_message("Logging system enabled. Member, moderation, moderation, message, and voice events will be tracked.", ephemeral=True)

    @app_commands.command(name="logging")
    @app_commands.describe(channel="Channel for logging", category="Category to target")
    async def logging(self, interaction: discord.Interaction, channel: discord.TextChannel, category: str = "general") -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can configure logging channels.", ephemeral=True)
            return
        self.bot.db.set_setting(interaction.guild_id, f"log_{category}", channel.id)
        await interaction.response.send_message(f"Set `{category}` logging channel to {channel.mention}.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Logging(bot))
