from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Owner(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    owner = app_commands.Group(name="owner", description="Owner-only tools")

    @owner.command(name="stats")
    async def stats(self, interaction: discord.Interaction) -> None:
        if interaction.user.id not in self.bot.settings.owner_ids:
            await interaction.response.send_message("This command is owner-only.", ephemeral=True)
            return
        embed = discord.Embed(title="PURIFY Status", color=discord.Color.red())
        embed.add_field(name="Guilds", value=str(len(self.bot.guilds)))
        embed.add_field(name="Users", value=str(sum(g.member_count for g in self.bot.guilds)))
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Owner(bot))
