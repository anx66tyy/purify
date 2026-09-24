from __future__ import annotations

import discord
from collections import defaultdict, deque
from datetime import timedelta
from time import monotonic
from discord import app_commands
from discord.ext import commands

from purify.core.checks import require_admin


class Security(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.message_bursts = defaultdict(lambda: deque(maxlen=12))
        self.join_bursts = defaultdict(lambda: deque(maxlen=20))

    security = app_commands.Group(name="security", description="Security controls")

    @security.command(name="status")
    async def status(self, interaction: discord.Interaction) -> None:
        if not await require_admin(interaction):
            return
        settings = self.bot.db.get_guild(interaction.guild_id)["settings"]
        embed = discord.Embed(title="PURIFY Security", color=discord.Color.green())
        embed.add_field(name="Anti-Nuke", value=str(settings.get("anti_nuke", "not configured")).title())
        embed.add_field(name="Anti-Raid", value="Enabled" if settings.get("anti_raid") else "Disabled")
        embed.add_field(name="Anti-Link", value="Enabled" if settings.get("anti_link") else "Disabled")
        embed.add_field(name="Anti-Spam", value="Enabled")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @security.command(name="antinuke")
    @app_commands.describe(action="setup, enable, disable")
    async def antinuke(self, interaction: discord.Interaction, action: str) -> None:
        if not await require_admin(interaction):
            return
        action = action.lower().strip()
        if action not in {"setup", "enable", "disable"}:
            await interaction.response.send_message("Use one of: `setup`, `enable`, or `disable`.", ephemeral=True)
            return
        self.bot.db.set_setting(interaction.guild_id, "anti_nuke", action)
        await interaction.response.send_message(f"✅ Anti-nuke action set to `{action}`.", ephemeral=True)

    @app_commands.command(name="antiraidsetup")
    async def antiraidsetup(self, interaction: discord.Interaction) -> None:
        if not await require_admin(interaction):
            return
        self.bot.db.set_setting(interaction.guild_id, "anti_raid", True)
        await interaction.response.send_message("✅ Anti-raid protection enabled.", ephemeral=True)

    @app_commands.command(name="antilinksetup")
    async def antilinksetup(self, interaction: discord.Interaction) -> None:
        if not await require_admin(interaction):
            return
        self.bot.db.set_setting(interaction.guild_id, "anti_link", True)
        await interaction.response.send_message("✅ Anti-link protection enabled.", ephemeral=True)

    @app_commands.command(name="quarantine")
    @app_commands.describe(user="User to quarantine")
    async def quarantine(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if not await require_admin(interaction):
            return
        if user == interaction.guild.owner or user.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message("❌ I cannot quarantine the server owner or someone above my role.", ephemeral=True)
            return
        role = discord.utils.get(interaction.guild.roles, name="Purify Quarantine")
        if role is None:
            role = await interaction.guild.create_role(name="Purify Quarantine", reason="PURIFY quarantine role")
        await user.add_roles(role, reason=f"Quarantined by {interaction.user}")
        await interaction.response.send_message(f"✅ {user.mention} has been quarantined.", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if not self.bot.db.get_setting(member.guild.id, "anti_raid", False):
            return
        now = monotonic()
        burst = self.join_bursts[member.guild.id]
        burst.append(now)
        while burst and now - burst[0] > 20:
            burst.popleft()
        if len(burst) >= 10:
            channel_id = self.bot.db.get_setting(member.guild.id, "log_security")
            channel = member.guild.get_channel(channel_id) if channel_id else None
            if isinstance(channel, discord.TextChannel):
                await channel.send(f"⚠️ Join burst detected in {member.guild.name}: {len(burst)} joins in 20 seconds.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return
        if self.bot.db.get_setting(message.guild.id, "anti_link", False):
            if "discord.gg/" in message.content.lower() or "discord.com/invite" in message.content.lower():
                if not message.author.guild_permissions.manage_messages:
                    try:
                        await message.delete()
                    except (discord.Forbidden, discord.HTTPException):
                        pass
                    try:
                        await message.author.timeout(discord.utils.utcnow() + timedelta(minutes=1), reason="Discord invite posted")
                    except (discord.Forbidden, discord.HTTPException):
                        pass
                    return

        events = self.message_bursts[(message.guild.id, message.author.id)]
        events.append(monotonic())
        while events and monotonic() - events[0] > 10:
            events.popleft()
        if len(events) >= 8 and not message.author.guild_permissions.manage_messages:
            try:
                await message.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass
            try:
                await message.author.timeout(discord.utils.utcnow() + timedelta(minutes=2), reason="Anti-spam")
            except (discord.Forbidden, discord.HTTPException):
                pass
            events.clear()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Security(bot))
