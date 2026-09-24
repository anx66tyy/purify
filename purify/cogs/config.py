from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Config(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="config", description="View the server PURIFY dashboard")
    async def config(self, interaction: discord.Interaction) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Administrator permission is required.", ephemeral=True)
            return
        guild = self.bot.db.get_guild(interaction.guild_id)
        settings = guild["settings"]
        embed = discord.Embed(title="🛡️ PURIFY Configuration", color=discord.Color.blurple())
        embed.add_field(name="Prefix", value=f"`{guild['prefix']}`")
        embed.add_field(name="Anti-nuke", value=str(settings.get("anti_nuke", "not configured")).title())
        embed.add_field(name="Anti-raid", value="Enabled" if settings.get("anti_raid") else "Not configured")
        embed.add_field(name="Anti-link", value="Enabled" if settings.get("anti_link") else "Not configured")
        embed.add_field(name="Tickets", value="Enabled" if settings.get("ticket_setup") else "Not configured")
        embed.add_field(name="Logging", value="Enabled" if settings.get("logging_enabled") else "Not configured")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="prefix", description="Set the server prefix for prefix commands")
    @app_commands.describe(prefix="One to five non-space characters")
    async def prefix(self, interaction: discord.Interaction, prefix: str) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Administrator permission is required.", ephemeral=True)
            return
        prefix = prefix.strip()
        if not prefix or len(prefix) > 5 or any(ch.isspace() for ch in prefix):
            await interaction.response.send_message("❌ Prefix must be 1–5 non-space characters.", ephemeral=True)
            return
        self.bot.db.set_prefix(interaction.guild_id, prefix)
        await interaction.response.send_message(f"✅ Prefix updated to `{prefix}`.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Config(bot))
