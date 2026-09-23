from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Leveling(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="levelsetup")
    async def levelsetup(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Leveling system initialized. XP, role rewards, and badges can be configured here.", ephemeral=True)

    @app_commands.command(name="rank")
    @app_commands.describe(user="User to inspect")
    async def rank(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        target = user or interaction.user
        xp, level = self.bot.db.get_xp(interaction.guild_id, target.id)
        embed = discord.Embed(title=f"{target.name}'s Rank", color=discord.Color.gold())
        embed.add_field(name="Level", value=str(level))
        embed.add_field(name="XP", value=str(xp))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leaderboard")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Leaderboard is ready for extension and XP reward configuration.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leveling(bot))
