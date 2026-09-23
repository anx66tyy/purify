from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Voice(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="voicemastersetup")
    async def voicemastersetup(self, interaction: discord.Interaction) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can configure VoiceMaster.", ephemeral=True)
            return
        await interaction.response.send_message("VoiceMaster setup initialized. Temporary voice channels and ownership controls can be configured here.", ephemeral=True)

    @app_commands.command(name="greetvoicesetup")
    @app_commands.describe(channel="Welcome voice channel", role="Restricted role", text="Welcome message")
    async def greetvoicesetup(self, interaction: discord.Interaction, channel: discord.VoiceChannel, role: discord.Role, text: str) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can configure greet voice.", ephemeral=True)
            return
        await interaction.response.send_message(f"Greet voice configured: {channel.mention}, role: {role.mention}, text: `{text}`.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Voice(bot))
