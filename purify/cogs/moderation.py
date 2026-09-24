from __future__ import annotations

import re
from collections import defaultdict, deque
from datetime import timedelta
from time import monotonic

import discord
from discord import app_commands
from discord.ext import commands


def parse_duration(raw: str) -> timedelta | None:
    if not raw:
        return None
    total = timedelta()
    matches = re.findall(r"(\d+)([smhdw])", raw.lower())
    if not matches:
        return None
    for value, unit in matches:
        value = int(value)
        if unit == "s":
            total += timedelta(seconds=value)
        elif unit == "m":
            total += timedelta(minutes=value)
        elif unit == "h":
            total += timedelta(hours=value)
        elif unit == "d":
            total += timedelta(days=value)
        elif unit == "w":
            total += timedelta(weeks=value)
    return total


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    mod = app_commands.Group(name="mod", description="Moderation controls")

    @mod.command(name="ban")
    @app_commands.describe(user="User to ban", reason="Reason")
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided") -> None:
        perms = interaction.user.guild_permissions
        if not (perms.ban_members or perms.administrator):
            await interaction.response.send_message("You do not have permission to ban members.", ephemeral=True)
            return
        if interaction.guild is None:
            return
        if user.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message("My highest role is not above the target.", ephemeral=True)
            return
        await user.ban(reason=reason)
        await interaction.response.send_message(f"Banned {user.mention}: {reason}", ephemeral=True)

    @mod.command(name="unban")
    @app_commands.describe(user_id="User ID to unban")
    async def unban(self, interaction: discord.Interaction, user_id: str) -> None:
        perms = interaction.user.guild_permissions
        if not (perms.ban_members or perms.administrator):
            await interaction.response.send_message("You do not have permission to unban members.", ephemeral=True)
            return
        if not user_id.isdigit():
            await interaction.response.send_message("Please provide a valid Discord user ID.", ephemeral=True)
            return
        bans = await interaction.guild.bans()
        target = discord.utils.get(bans, user__id=int(user_id))
        if target is None:
            await interaction.response.send_message("That user is not currently banned.", ephemeral=True)
            return
        await interaction.guild.unban(target.user)
        await interaction.response.send_message(f"Unbanned {target.user.mention}.", ephemeral=True)

    @mod.command(name="kick")
    @app_commands.describe(user="User to kick", reason="Reason")
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided") -> None:
        perms = interaction.user.guild_permissions
        if not (perms.kick_members or perms.administrator):
            await interaction.response.send_message("You do not have permission to kick members.", ephemeral=True)
            return
        if interaction.guild is None:
            return
        if user.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message("My highest role is not above the target.", ephemeral=True)
            return
        await user.kick(reason=reason)
        await interaction.response.send_message(f"Kicked {user.mention}: {reason}", ephemeral=True)

    @mod.command(name="timeout")
    @app_commands.describe(user="User to timeout", duration="Duration like 10m or 1h", reason="Reason")
    async def timeout(self, interaction: discord.Interaction, user: discord.Member, duration: str, reason: str = "No reason provided") -> None:
        perms = interaction.user.guild_permissions
        if not (perms.moderate_members or perms.administrator):
            await interaction.response.send_message("You do not have permission to timeout members.", ephemeral=True)
            return
        td = parse_duration(duration)
        if td is None:
            await interaction.response.send_message("Use a valid duration such as `10m`, `1h`, or `7d`.", ephemeral=True)
            return
        await user.timeout(discord.utils.utcnow() + td, reason=reason)
        await interaction.response.send_message(f"Timed out {user.mention} for {duration}.", ephemeral=True)

    @mod.command(name="untimeout")
    @app_commands.describe(user="User to remove timeout from")
    async def untimeout(self, interaction: discord.Interaction, user: discord.Member) -> None:
        perms = interaction.user.guild_permissions
        if not (perms.moderate_members or perms.administrator):
            await interaction.response.send_message("You do not have permission to remove timeouts.", ephemeral=True)
            return
        await user.timeout(None)
        await interaction.response.send_message(f"Removed timeout from {user.mention}.", ephemeral=True)

    @mod.command(name="warn")
    @app_commands.describe(user="User to warn", reason="Reason")
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided") -> None:
        perms = interaction.user.guild_permissions
        if not (perms.moderate_members or perms.administrator):
            await interaction.response.send_message("You do not have permission to warn members.", ephemeral=True)
            return
        self.bot.db.add_warning(interaction.guild_id, user.id, interaction.user.id, reason)
        await interaction.response.send_message(f"Warned {user.mention}: {reason}", ephemeral=True)

    @mod.command(name="warns")
    @app_commands.describe(user="User to inspect")
    async def warns(self, interaction: discord.Interaction, user: discord.Member) -> None:
        perms = interaction.user.guild_permissions
        if not (perms.moderate_members or perms.administrator):
            await interaction.response.send_message("You do not have permission to view warnings.", ephemeral=True)
            return
        rows = self.bot.db.get_warnings(interaction.guild_id, user.id)
        embed = discord.Embed(title=f"Warnings for {user}", color=discord.Color.orange())
        if not rows:
            embed.description = "No warnings found."
        else:
            for row in rows[:5]:
                embed.add_field(name=f"Warning #{row['id']}", value=row['reason'] or "No reason provided", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @mod.command(name="purge")
    @app_commands.describe(amount="Messages to delete", user="Optional target user")
    async def purge(self, interaction: discord.Interaction, amount: int, user: discord.Member | None = None) -> None:
        perms = interaction.user.guild_permissions
        if not (perms.manage_messages or perms.administrator):
            await interaction.response.send_message("You do not have permission to purge messages.", ephemeral=True)
            return
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This command must be used in a text channel.", ephemeral=True)
            return
        if amount < 1 or amount > 200:
            await interaction.response.send_message("Amount must be between 1 and 200.", ephemeral=True)
            return
        messages = []
        async for message in interaction.channel.history(limit=amount):
            if user is None or message.author == user:
                messages.append(message)
        if messages:
            await interaction.channel.delete_messages(messages)
        await interaction.response.send_message(f"Deleted {len(messages)} message(s).", ephemeral=True)

    @mod.command(name="softban")
    @app_commands.describe(user="User to softban", reason="Reason")
    async def softban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided") -> None:
        perms = interaction.user.guild_permissions
        if not (perms.ban_members or perms.administrator):
            await interaction.response.send_message("You do not have permission to softban members.", ephemeral=True)
            return
        await user.ban(reason=reason, delete_message_days=1)
        await interaction.guild.unban(user, reason=f"Softban completed: {reason}")
        await interaction.response.send_message(f"Softbanned {user.mention}: {reason}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
