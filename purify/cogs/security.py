from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from purify.core.checks import require_moderator


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    mod = app_commands.Group(name="mod", description="Moderation commands")

    @mod.command(name="ban")
    @app_commands.describe(user="Member to ban", reason="Reason for the ban")
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided") -> None:
        if not await require_moderator(interaction):
            return
        if interaction.guild is None:
            return
        if user.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message("My role is not high enough to ban that member.", ephemeral=True)
            return
        await user.ban(reason=reason)
        await interaction.response.send_message(f"Banned {user.mention} for: {reason}", ephemeral=True)

    @mod.command(name="kick")
    @app_commands.describe(user="Member to kick", reason="Reason for the kick")
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided") -> None:
        if not await require_moderator(interaction):
            return
        if user.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message("My role is not high enough to kick that member.", ephemeral=True)
            return
        await user.kick(reason=reason)
        await interaction.response.send_message(f"Kicked {user.mention} for: {reason}", ephemeral=True)

    @mod.command(name="warn")
    @app_commands.describe(user="Member to warn", reason="Warning reason")
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided") -> None:
        if not await require_moderator(interaction):
            return
        self.bot.db.add_warning(interaction.guild_id, user.id, interaction.user.id, reason)
        await interaction.response.send_message(f"Warned {user.mention} for: {reason}", ephemeral=True)

    @mod.command(name="warns")
    @app_commands.describe(user="User to inspect")
    async def warns(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if not await require_moderator(interaction):
            return
        warnings = self.bot.db.get_warnings(interaction.guild_id, user.id)
        embed = discord.Embed(title=f"Warnings for {user}", color=discord.Color.orange())
        if warnings:
            for warning in warnings:
                embed.add_field(name=f"Warning #{warning['id']}", value=warning['reason'] or "No reason provided", inline=False)
        else:
            embed.description = "No warnings found."
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @mod.command(name="purge")
    @app_commands.describe(amount="Number of messages to delete", user="Optional target user")
    async def purge(self, interaction: discord.Interaction, amount: int, user: discord.Member | None = None) -> None:
        if not await require_moderator(interaction):
            return
        if amount < 1 or amount > 200:
            await interaction.response.send_message("Amount must be between 1 and 200.", ephemeral=True)
            return
        if interaction.channel is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This command must be used in a text channel.", ephemeral=True)
            return
        deleted = 0
        async for message in interaction.channel.history(limit=amount):
            if user is None or message.author == user:
                deleted += 1
        messages = []
        async for message in interaction.channel.history(limit=amount):
            if user is None or message.author == user:
                messages.append(message)
        if messages:
            await interaction.channel.delete_messages(messages)
        await interaction.response.send_message(f"Deleted {deleted} message(s).", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
