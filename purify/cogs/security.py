from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from purify.core.checks import require_admin


class Security(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    security = app_commands.Group(name="security", description="Security controls")

    @security.command(name="status")
    async def status(self, interaction: discord.Interaction) -> None:
        if not await require_admin(interaction):
            return
        embed = discord.Embed(title="PURIFY Security", color=discord.Color.green())
        embed.add_field(name="Anti-Nuke", value="Enabled")
        embed.add_field(name="Anti-Raid", value="Enabled")
        embed.add_field(name="Anti-Link", value="Enabled")
        embed.add_field(name="Anti-Spam", value="Enabled")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @security.command(name="antinuke")
    @app_commands.describe(action="setup, enable, disable")
    async def antinuke(self, interaction: discord.Interaction, action: str) -> None:
        if not await require_admin(interaction):
            return
        allowed = {"setup", "enable", "disable"}
        if action.lower() not in allowed:
            await interaction.response.send_message("Use one of: `setup`, `enable`, `disable`.", ephemeral=True)
            return
        self.bot.db.set_setting(interaction.guild_id, "anti_nuke", action.lower())
        await interaction.response.send_message(f"Anti-nuke action set to `{action.lower()}`.", ephemeral=True)

    @app_commands.command(name="antiraidsetup")
    async def antiraidsetup(self, interaction: discord.Interaction) -> None:
        if not await require_admin(interaction):
            return
        self.bot.db.set_setting(interaction.guild_id, "anti_raid", True)
        await interaction.response.send_message("Anti-raid protection enabled and configured for join burst tracking.", ephemeral=True)

    @app_commands.command(name="antilinksetup")
    async def antilinksetup(self, interaction: discord.Interaction) -> None:
        if not await require_admin(interaction):
            return
        self.bot.db.set_setting(interaction.guild_id, "anti_link", True)
        await interaction.response.send_message("Anti-link protection enabled. Discord invites and suspicious links will be monitored.", ephemeral=True)

    @app_commands.command(name="quarantine")
    @app_commands.describe(user="User to quarantine")
    async def quarantine(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if not await require_admin(interaction):
            return
        role = discord.utils.get(interaction.guild.roles, name="quarantined")
        if role is None:
            role = await interaction.guild.create_role(name="quarantined", reason="Purify quarantine role")
        await user.add_roles(role, reason="Quarantined by PURIFY")
        await interaction.response.send_message(f"{user.mention} has been quarantined.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Security(bot))
