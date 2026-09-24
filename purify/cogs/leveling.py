from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Leveling(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="levelsetup", description="Initialize XP leveling")
    async def levelsetup(self, interaction: discord.Interaction) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
            return
        self.bot.db.set_setting(interaction.guild_id, "leveling_enabled", True)
        await interaction.response.send_message("✅ Leveling system enabled.", ephemeral=True)

    @app_commands.command(name="rank", description="View a user's rank")
    @app_commands.describe(user="User to inspect")
    async def rank(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        target = user or interaction.user
        xp, level = self.bot.db.get_xp(interaction.guild_id, target.id)
        embed = discord.Embed(title=f"{target.name}'s Rank", color=discord.Color.gold())
        embed.add_field(name="Level", value=str(level))
        embed.add_field(name="XP", value=str(xp))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leaderboard", description="View the server leaderboard")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("🏆 Leaderboard is ready for expansion with rank card and reward logic.", ephemeral=True)

    xp = app_commands.Group(name="xp", description="XP management")

    @xp.command(name="add", description="Award XP to a user")
    @app_commands.describe(user="User to award", amount="XP amount")
    async def add_xp(self, interaction: discord.Interaction, user: discord.Member, amount: int) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
            return
        total_xp, level = self.bot.db.add_xp(interaction.guild_id, user.id, amount)
        await interaction.response.send_message(f"✅ Awarded {amount} XP to {user.mention}. Total: {total_xp}. Level: {level}.", ephemeral=True)

    @xp.command(name="remove", description="Remove XP from a user")
    @app_commands.describe(user="User to affect", amount="XP amount")
    async def remove_xp(self, interaction: discord.Interaction, user: discord.Member, amount: int) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)
            return
        current_xp, _ = self.bot.db.get_xp(interaction.guild_id, user.id)
        new_xp = max(0, current_xp - amount)
        self.bot.db.add_xp(interaction.guild_id, user.id, -amount)
        await interaction.response.send_message(f"✅ Removed {amount} XP from {user.mention}. New total: {new_xp}.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leveling(bot))
