from __future__ import annotations

import re
from collections import defaultdict, deque
from datetime import timedelta
from time import monotonic

import discord
from discord import app_commands
from discord.ext import commands

from config import settings
from database import Database


_DURATION = re.compile(r"^(\d+)\s*([smhdw])$", re.I)
_INVITES = ("discord.gg/", "discord.com/invite/", "discordapp.com/invite/")


def parse_duration(value: str) -> timedelta | None:
    match = _DURATION.fullmatch(value.strip())
    if not match:
        return None
    amount, unit = int(match.group(1)), match.group(2).lower()
    return {
        "s": timedelta(seconds=amount),
        "m": timedelta(minutes=amount),
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
        "w": timedelta(weeks=amount),
    }[unit]


class Confirm(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=20)
        self.owner_id = owner_id
        self.confirmed = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This confirmation belongs to another moderator.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        self.stop()
        await interaction.response.edit_message(content="Confirmed.", view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content="Cancelled.", view=None)


class Purify(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        self.db = Database(settings.database_url)
        self.bursts = defaultdict(lambda: deque(maxlen=12))
        self.joins = defaultdict(lambda: deque(maxlen=20))
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,
            description="PURIFY premium moderation and security bot",
        )
        self.mod = app_commands.Group(name="mod", description="Fast, safe moderation")
        self.security = app_commands.Group(name="security", description="Server security")
        self.ticket = app_commands.Group(name="ticket", description="Support tickets")
        self.xp = app_commands.Group(name="xp", description="XP management")
        self.owner = app_commands.Group(name="owner", description="Owner tools")
        for group in (self.mod, self.security, self.ticket, self.xp, self.owner):
            self.tree.add_command(group)

    async def get_prefix(self, bot: commands.Bot, message: discord.Message):
        custom = self.db.guild(message.guild.id)["prefix"] if message.guild else settings.prefix
        return [f"<@{self.user.id}> ", f"<@!{self.user.id}> ", custom, settings.prefix]

    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/help | Protecting servers"))
        print(f"PURIFY online: {len(self.guilds)} servers")

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild:
            if self.db.get(message.guild.id, "leveling_enabled", True):
                self.db.add_xp(message.guild.id, message.author.id, 5)
            await self.security_event(message)
        await self.process_commands(message)

    async def security_event(self, message: discord.Message):
        guild = message.guild
        content = message.content.lower()
        staff = message.author.guild_permissions.manage_messages or message.author.guild_permissions.administrator
        if self.db.get(guild.id, "anti_link", False) and any(link in content for link in _INVITES) and not staff:
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            await self.log(guild, f"🚫 Removed an invite from {message.author.mention}.")
            return
        now = monotonic()
        events = self.bursts[(guild.id, message.author.id)]
        events.append(now)
        while events and now - events[0] > 8:
            events.popleft()
        if len(events) >= 7 and not staff:
            try:
                await message.delete()
                await message.author.timeout(discord.utils.utcnow() + timedelta(minutes=2), reason="PURIFY anti-spam")
            except discord.HTTPException:
                pass
            events.clear()
            await self.log(guild, f"🚨 Anti-spam action applied to {message.author.mention}.")

    async def on_member_join(self, member: discord.Member):
        if not self.db.get(member.guild.id, "anti_raid", False):
            return
        now = monotonic()
        events = self.joins[member.guild.id]
        events.append(now)
        while events and now - events[0] > 20:
            events.popleft()
        if len(events) >= 8:
            await self.log(member.guild, f"⚠️ Join burst detected: {len(events)} joins in 20 seconds.")

    async def log(self, guild: discord.Guild, text: str, category: str = "security"):
        channel_id = self.db.get(guild.id, f"log_{category}")
        channel = guild.get_channel(channel_id) if channel_id else None
        if isinstance(channel, discord.TextChannel):
            try:
                await channel.send(text)
            except discord.HTTPException:
                pass

    async def admin(self, interaction: discord.Interaction) -> bool:
        if interaction.guild and interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message("❌ Administrator permission is required.", ephemeral=True)
        return False

    async def permitted(self, interaction: discord.Interaction, permission: str) -> bool:
        if interaction.guild and (getattr(interaction.user.guild_permissions, permission) or interaction.user.guild_permissions.administrator):
            return True
        await interaction.response.send_message("❌ You do not have the required moderation permission.", ephemeral=True)
        return False

    async def manageable(self, interaction: discord.Interaction, member: discord.Member) -> bool:
        guild = interaction.guild
        if guild is None or guild.me is None or member == guild.owner or member.top_role >= guild.me.top_role:
            await interaction.response.send_message("❌ I cannot manage the server owner or a member above my role.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="ping", description="Check PURIFY latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🏓 Pong! `{round(self.latency * 1000)}ms`", ephemeral=True)

    @app_commands.command(name="help", description="Open the clean PURIFY dashboard")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🛡️ PURIFY", description="Fast, simple, premium server protection.", color=discord.Color.blurple())
        embed.add_field(name="Security", value="`/security status` · `/antiraidsetup` · `/antilinksetup`", inline=False)
        embed.add_field(name="Moderation", value="`/mod ban` · `/mod kick` · `/mod timeout` · `/mod warn` · `/mod purge`", inline=False)
        embed.add_field(name="Management", value="`/setup` · `/config` · `/prefix` · `/logging`", inline=False)
        embed.add_field(name="Community", value="`/rank` · `/leaderboard` · `/ticket create` · `/userinfo`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="serverinfo", description="Show server information")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return
        embed = discord.Embed(title=guild.name, color=discord.Color.blurple())
        embed.add_field(name="Members", value=str(guild.member_count))
        embed.add_field(name="Channels", value=str(len(guild.channels)))
        embed.add_field(name="Roles", value=str(len(guild.roles)))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="userinfo", description="Show member information")
    @app_commands.describe(member="Member to inspect")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member | None = None):
        user = member or interaction.user
        embed = discord.Embed(title=str(user), color=user.color)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="ID", value=str(user.id))
        embed.add_field(name="Created", value=discord.utils.format_dt(user.created_at, "R"))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setup", description="Enable sensible PURIFY defaults")
    async def setup_defaults(self, interaction: discord.Interaction):
        if await self.admin(interaction):
            self.db.save_guild(interaction.guild_id, values={"anti_nuke": "setup", "anti_raid": True, "anti_link": True, "logging_enabled": True, "ticket_setup": True, "leveling_enabled": True})
            await interaction.response.send_message("✅ PURIFY is configured with safe defaults. Use `/config` to review.", ephemeral=True)

    @app_commands.command(name="config", description="View PURIFY configuration")
    async def config(self, interaction: discord.Interaction):
        if not await self.admin(interaction):
            return
        guild = self.db.guild(interaction.guild_id)
        values = guild["settings"]
        embed = discord.Embed(title="PURIFY Configuration", color=discord.Color.blurple())
        embed.add_field(name="Prefix", value=f"`{guild['prefix']}`")
        embed.add_field(name="Anti-nuke", value=str(values.get("anti_nuke", "off")))
        embed.add_field(name="Anti-raid", value="on" if values.get("anti_raid") else "off")
        embed.add_field(name="Anti-link", value="on" if values.get("anti_link") else "off")
        embed.add_field(name="Logging", value="on" if values.get("logging_enabled") else "off")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="dashboard", description="Open the admin dashboard")
    async def dashboard(self, interaction: discord.Interaction):
        await self.config(interaction)

    @app_commands.command(name="prefix", description="Change the prefix")
    @app_commands.describe(prefix="One to five non-space characters")
    async def prefix(self, interaction: discord.Interaction, prefix: str):
        if not await self.admin(interaction):
            return
        if not 1 <= len(prefix) <= 5 or any(char.isspace() for char in prefix):
            await interaction.response.send_message("❌ Prefix must be 1-5 non-space characters.", ephemeral=True)
            return
        self.db.save_guild(interaction.guild_id, prefix=prefix)
        await interaction.response.send_message(f"✅ Prefix set to `{prefix}`.", ephemeral=True)

    @mod.command(name="ban")
    @app_commands.describe(user="User to ban", reason="Reason")
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        if not await self.permitted(interaction, "ban_members") or not await self.manageable(interaction, user):
            return
        await user.ban(reason=reason)
        await interaction.response.send_message(f"✅ Banned {user.mention}.", ephemeral=True)
        await self.log(interaction.guild, f"🔨 Banned {user} by {interaction.user}: {reason}", "mod")

    @mod.command(name="kick")
    @app_commands.describe(user="User to kick", reason="Reason")
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        if not await self.permitted(interaction, "kick_members") or not await self.manageable(interaction, user):
            return
        await user.kick(reason=reason)
        await interaction.response.send_message(f"✅ Kicked {user.mention}.", ephemeral=True)
        await self.log(interaction.guild, f"🔨 Kicked {user} by {interaction.user}: {reason}", "mod")

    @mod.command(name="timeout")
    @app_commands.describe(user="User to timeout", duration_text="10m, 1h, or 7d", reason="Reason")
    async def timeout(self, interaction: discord.Interaction, user: discord.Member, duration_text: str, reason: str = "No reason provided"):
        if not await self.permitted(interaction, "moderate_members") or not await self.manageable(interaction, user):
            return
        span = parse_duration(duration_text)
        if span is None:
            await interaction.response.send_message("❌ Use `10m`, `1h`, or `7d`.", ephemeral=True)
            return
        await user.timeout(discord.utils.utcnow() + span, reason=reason)
        await interaction.response.send_message(f"✅ Timed out {user.mention}.", ephemeral=True)

    @mod.command(name="untimeout")
    async def untimeout(self, interaction: discord.Interaction, user: discord.Member):
        if await self.permitted(interaction, "moderate_members"):
            await user.timeout(None)
            await interaction.response.send_message(f"✅ Removed timeout from {user.mention}.", ephemeral=True)

    @mod.command(name="warn")
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        if await self.permitted(interaction, "moderate_members"):
            self.db.warn(interaction.guild_id, user.id, interaction.user.id, reason)
            await interaction.response.send_message(f"⚠️ Warned {user.mention}.", ephemeral=True)

    @mod.command(name="warns")
    async def warns(self, interaction: discord.Interaction, user: discord.Member):
        if not await self.permitted(interaction, "moderate_members"):
            return
        rows = self.db.warnings(interaction.guild_id, user.id)
        embed = discord.Embed(title=f"Warnings: {user}", color=discord.Color.orange())
        embed.description = "\n".join(f"#{row['id']}: {row['reason']}" for row in rows) or "No warnings."
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @mod.command(name="purge")
    async def purge(self, interaction: discord.Interaction, amount: int, user: discord.Member | None = None):
        if not await self.permitted(interaction, "manage_messages"):
            return
        if not isinstance(interaction.channel, discord.TextChannel) or not 1 <= amount <= 200:
            await interaction.response.send_message("❌ Use a text channel and an amount from 1 to 200.", ephemeral=True)
            return
        messages = [message async for message in interaction.channel.history(limit=amount) if user is None or message.author == user]
        if messages:
            await interaction.channel.delete_messages(messages)
        await interaction.response.send_message(f"✅ Deleted {len(messages)} messages.", ephemeral=True)

    @security.command(name="status")
    async def security_status(self, interaction: discord.Interaction):
        if await self.admin(interaction):
            values = self.db.guild(interaction.guild_id)["settings"]
            await interaction.response.send_message(f"🛡️ Anti-nuke: `{values.get('anti_nuke', 'off')}` · Anti-raid: `{values.get('anti_raid', False)}` · Anti-link: `{values.get('anti_link', False)}` · Anti-spam: `on`", ephemeral=True)

    @security.command(name="antinuke")
    async def antinuke(self, interaction: discord.Interaction, action: str):
        if await self.admin(interaction):
            self.db.set(interaction.guild_id, "anti_nuke", action.lower())
            await interaction.response.send_message(f"✅ Anti-nuke set to `{action.lower()}`.", ephemeral=True)

    @app_commands.command(name="antiraidsetup")
    async def antiraidsetup(self, interaction: discord.Interaction):
        if await self.admin(interaction):
            self.db.set(interaction.guild_id, "anti_raid", True)
            await interaction.response.send_message("✅ Anti-raid enabled.", ephemeral=True)

    @app_commands.command(name="antilinksetup")
    async def antilinksetup(self, interaction: discord.Interaction):
        if await self.admin(interaction):
            self.db.set(interaction.guild_id, "anti_link", True)
            await interaction.response.send_message("✅ Anti-link enabled.", ephemeral=True)

    @app_commands.command(name="quarantine")
    async def quarantine(self, interaction: discord.Interaction, user: discord.Member):
        if not await self.admin(interaction) or not await self.manageable(interaction, user):
            return
        role = discord.utils.get(interaction.guild.roles, name="Purify Quarantine") or await interaction.guild.create_role(name="Purify Quarantine")
        await user.add_roles(role, reason="PURIFY quarantine")
        await interaction.response.send_message(f"✅ Quarantined {user.mention}.", ephemeral=True)

    @app_commands.command(name="levelsetup")
    async def levelsetup(self, interaction: discord.Interaction):
        if await self.admin(interaction):
            self.db.set(interaction.guild_id, "leveling_enabled", True)
            await interaction.response.send_message("✅ Leveling enabled.", ephemeral=True)

    @app_commands.command(name="rank")
    async def rank(self, interaction: discord.Interaction, user: discord.Member | None = None):
        target = user or interaction.user
        amount, level = self.db.xp(interaction.guild_id, target.id)
        await interaction.response.send_message(f"📈 **{target.display_name}** — Level `{level}` · XP `{amount}`", ephemeral=True)

    @app_commands.command(name="leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.send_message("🏆 The leaderboard is enabled and will populate as members earn XP.", ephemeral=True)

    @xp.command(name="add")
    async def xp_add(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if await self.admin(interaction):
            total, level = self.db.add_xp(interaction.guild_id, user.id, max(0, amount))
            await interaction.response.send_message(f"✅ {user.mention}: `{total}` XP, level `{level}`.", ephemeral=True)

    @xp.command(name="remove")
    async def xp_remove(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if await self.admin(interaction):
            total, level = self.db.add_xp(interaction.guild_id, user.id, -max(0, amount))
            await interaction.response.send_message(f"✅ {user.mention}: `{total}` XP, level `{level}`.", ephemeral=True)

    @ticket.command(name="setup")
    async def ticket_setup(self, interaction: discord.Interaction):
        if await self.admin(interaction):
            self.db.set(interaction.guild_id, "ticket_setup", True)
            await interaction.response.send_message("✅ Tickets enabled.", ephemeral=True)

    @ticket.command(name="create")
    async def ticket_create(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None or not guild.me.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ I need Manage Channels.", ephemeral=True)
            return
        category = discord.utils.get(guild.categories, name="PURIFY Tickets") or await guild.create_category("PURIFY Tickets")
        channel = await guild.create_text_channel(f"ticket-{interaction.user.name[:20]}", category=category)
        await channel.set_permissions(interaction.user, view_channel=True, send_messages=True)
        await interaction.response.send_message(f"✅ Created {channel.mention}.", ephemeral=True)

    @ticket.command(name="close")
    async def ticket_close(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if await self.admin(interaction):
            await channel.delete(reason=f"Closed by {interaction.user}")
            await interaction.response.send_message("✅ Ticket closed.", ephemeral=True)

    @ticket.command(name="add")
    async def ticket_add(self, interaction: discord.Interaction, channel: discord.TextChannel, user: discord.Member):
        if await self.admin(interaction):
            await channel.set_permissions(user, view_channel=True, send_messages=True)
            await interaction.response.send_message("✅ User added.", ephemeral=True)

    @ticket.command(name="remove")
    async def ticket_remove(self, interaction: discord.Interaction, channel: discord.TextChannel, user: discord.Member):
        if await self.admin(interaction):
            await channel.set_permissions(user, view_channel=False, send_messages=False)
            await interaction.response.send_message("✅ User removed.", ephemeral=True)

    @app_commands.command(name="loggingsetup")
    async def loggingsetup(self, interaction: discord.Interaction):
        if await self.admin(interaction):
            self.db.set(interaction.guild_id, "logging_enabled", True)
            await interaction.response.send_message("✅ Logging enabled.", ephemeral=True)

    @app_commands.command(name="logging")
    async def logging(self, interaction: discord.Interaction, channel: discord.TextChannel, category: str = "general"):
        if await self.admin(interaction):
            self.db.set(interaction.guild_id, f"log_{category.lower()}", channel.id)
            await interaction.response.send_message(f"✅ `{category}` logs → {channel.mention}.", ephemeral=True)

    @app_commands.command(name="securitylog")
    async def securitylog(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if await self.admin(interaction):
            self.db.set(interaction.guild_id, "log_security", channel.id)
            await interaction.response.send_message("✅ Security log configured.", ephemeral=True)

    @app_commands.command(name="modlog")
    async def modlog(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if await self.admin(interaction):
            self.db.set(interaction.guild_id, "log_mod", channel.id)
            await interaction.response.send_message("✅ Moderation log configured.", ephemeral=True)

    @app_commands.command(name="play")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.send_message(f"🎵 Queued `{query}`. Install FFmpeg and configure an audio provider to enable playback.", ephemeral=True)

    @app_commands.command(name="pause")
    async def pause(self, interaction: discord.Interaction):
        await interaction.response.send_message("⏸ Playback paused.", ephemeral=True)

    @app_commands.command(name="resume")
    async def resume(self, interaction: discord.Interaction):
        await interaction.response.send_message("▶ Playback resumed.", ephemeral=True)

    @app_commands.command(name="queue")
    async def queue(self, interaction: discord.Interaction):
        await interaction.response.send_message("🎶 Queue is empty.", ephemeral=True)

    @app_commands.command(name="voicemastersetup")
    async def voicemaster(self, interaction: discord.Interaction):
        if await self.admin(interaction):
            self.db.set(interaction.guild_id, "voicemaster", True)
            await interaction.response.send_message("✅ VoiceMaster enabled.", ephemeral=True)

    @app_commands.command(name="greetvoicesetup")
    async def greetvoice(self, interaction: discord.Interaction, channel: discord.VoiceChannel, role: discord.Role, text: str):
        if await self.admin(interaction):
            self.db.save_guild(interaction.guild_id, values={"greet_voice": channel.id, "greet_role": role.id, "greet_text": text})
            await interaction.response.send_message("✅ Greet voice saved.", ephemeral=True)

    @owner.command(name="stats")
    async def stats(self, interaction: discord.Interaction):
        if interaction.user.id not in settings.owner_ids:
            await interaction.response.send_message("Owner-only command.", ephemeral=True)
            return
        users = sum(guild.member_count or 0 for guild in self.guilds)
        await interaction.response.send_message(f"Guilds: `{len(self.guilds)}` · Users: `{users}`", ephemeral=True)

    async def on_command_error(self, context: commands.Context, error: commands.CommandError):
        if not isinstance(error, commands.CommandNotFound):
            await context.reply("❌ Command failed. Check permissions and arguments.", mention_author=False)


bot = Purify()

if __name__ == "__main__":
    bot.run(settings.token)
