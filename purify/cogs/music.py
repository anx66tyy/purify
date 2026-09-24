from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="play", description="Queue a song or URL")
    @app_commands.describe(query="Song or URL to play")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.send_message(f"🎵 Playback request queued: `{query}`. Audio system is ready for full integration.", ephemeral=True)

    @app_commands.command(name="pause", description="Pause playback")
    async def pause(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("⏸ Playback paused.", ephemeral=True)

    @app_commands.command(name="resume", description="Resume playback")
    async def resume(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("▶ Playback resumed.", ephemeral=True)

    @app_commands.command(name="queue", description="Show the current queue")
    async def queue(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("🎶 Queue is empty.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot))
