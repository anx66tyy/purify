from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Config(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="config")
    async def config(self, interaction: discord.Interaction) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("This command requires administrator permissions.", ephemeral=True)
            return
        guild = self.bot.db.get_guild(interaction.guild_id)
        embed = discord.Embed(title="PURIFY Configuration", color=discord.Color.blurple())
        embed.add_field(name="Prefix", value=guild["prefix"])
        embed.add_field(name="Security", value="Enabled")
        embed.add_field(name="Moderation", value="Enabled")
        embed.add_field(name="Leveling", value="Enabled")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="prefix")
    @app_commands.describe(prefix="The new guild prefix")
    async def prefix(self, interaction: discord.Interaction, prefix: str) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions to change the prefix.", ephemeral=True)
            return
        self.bot.db.set_prefix(interaction.guild_id, prefix)
        await interaction.response.send_message(f"Guild prefix updated to `{prefix}`.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Config(bot))
