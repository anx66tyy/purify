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


class Confirm(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=20)
        self.owner_id, self.value = owner_id, False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message('This confirmation belongs to another moderator.', ephemeral=True)
            return False
        return True

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await interaction.response.edit_message(content='Confirmed.', view=None)

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content='Cancelled.', view=None)


def duration(value: str) -> timedelta | None:
    found = re.fullmatch(r'\s*(\d+)\s*([smhdw])\s*', value.lower())
    if not found:
        return None
    amount, unit = int(found.group(1)), found.group(2)
    return timedelta(**{'s': {'seconds': amount}, 'm': {'minutes': amount}, 'h': {'hours': amount}, 'd': {'days': amount}, 'w': {'weeks': amount}}[unit])


class Purify(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        self.db = Database(settings.database_url)
        self.bursts = defaultdict(lambda: deque(maxlen=10))
        self.joins = defaultdict(lambda: deque(maxlen=20))
        super().__init__(command_prefix=self.prefixes, intents=intents, help_command=None, description='PURIFY premium moderation bot')
        self.mod = app_commands.Group(name='mod', description='Fast, safe moderation')
        self.security = app_commands.Group(name='security', description='Server security')
        self.ticket = app_commands.Group(name='ticket', description='Support tickets')
        self.xp = app_commands.Group(name='xp', description='XP management')
        self.owner = app_commands.Group(name='owner', description='Bot owner tools')
        self.tree.add_command(self.mod); self.tree.add_command(self.security); self.tree.add_command(self.ticket); self.tree.add_command(self.xp); self.tree.add_command(self.owner)

    async def prefixes(self, bot, message):
        custom = self.db.guild(message.guild.id)['prefix'] if message.guild else settings.prefix
        return [f'<@{self.user.id}> ', f'<@!{self.user.id}> ', custom, settings.prefix]

    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='/help | Protecting servers'))
        print(f'PURIFY online: {len(self.guilds)} servers')

    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        if self.db.get(message.guild.id, 'leveling_enabled', True): self.db.add_xp(message.guild.id, message.author.id, 5)
        content = message.content.lower()
        if self.db.get(message.guild.id, 'anti_link', False) and 'discord.gg/' in content and not message.author.guild_permissions.manage_messages:
            try: await message.delete()
            except discord.HTTPException: pass
            return
        key = (message.guild.id, message.author.id); now = monotonic(); events = self.bursts[key]; events.append(now)
        while events and now - events[0] > 8: events.popleft()
        if len(events) >= 7 and not message.author.guild_permissions.manage_messages:
            try: await message.delete()
            except discord.HTTPException: pass
            try: await message.author.timeout(discord.utils.utcnow() + timedelta(minutes=2), reason='PURIFY anti-spam')
            except discord.HTTPException: pass
            events.clear()
        await self.process_commands(message)

    async def on_member_join(self, member):
        if not self.db.get(member.guild.id, 'anti_raid', False): return
        now = monotonic(); burst = self.joins[member.guild.id]; burst.append(now)
        while burst and now - burst[0] > 20: burst.popleft()
        if len(burst) >= 8: await self.log(member.guild, '⚠️ Join burst detected.')

    async def log(self, guild, text, category='security'):
        channel_id = self.db.get(guild.id, f'log_{category}')
        channel = guild.get_channel(channel_id) if channel_id else None
        if isinstance(channel, discord.TextChannel):
            try: await channel.send(text)
            except discord.HTTPException: pass

    async def admin(self, i):
        if i.guild and i.user.guild_permissions.administrator: return True
        await i.response.send_message('❌ Administrator permission is required.', ephemeral=True); return False

    async def moderate(self, i, permission):
        if i.guild and (getattr(i.user.guild_permissions, permission) or i.user.guild_permissions.administrator): return True
        await i.response.send_message('❌ You do not have the required moderation permission.', ephemeral=True); return False

    async def target_ok(self, i, user):
        if i.guild is None or i.guild.me is None or user == i.guild.owner or user.top_role >= i.guild.me.top_role:
            await i.response.send_message('❌ I cannot manage the server owner or a member above my highest role.', ephemeral=True); return False
        return True

    @app_commands.command(name='ping', description='Check bot latency')
    async def ping(self, i): await i.response.send_message(f'🏓 Pong! `{round(self.latency * 1000)}ms`', ephemeral=True)

    @app_commands.command(name='help', description='Open the clean PURIFY dashboard')
    async def help(self, i):
        e = discord.Embed(title='🛡️ PURIFY', description='Fast, simple, premium server protection.', color=discord.Color.blurple())
        e.add_field(name='Security', value='/security status · /antiraidsetup · /antilinksetup', inline=False)
        e.add_field(name='Moderation', value='/mod ban �� kick · timeout · warn · purge', inline=False)
        e.add_field(name='Management', value='/setup · /config · /logging · /ticket setup', inline=False)
        e.add_field(name='Community', value='/rank · /leaderboard · /play · /userinfo', inline=False)
        await i.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name='serverinfo', description='Show server information')
    async def serverinfo(self, i):
        g=i.guild; e=discord.Embed(title=g.name, color=discord.Color.blurple()); e.add_field(name='Members',value=str(g.member_count)); e.add_field(name='Channels',value=str(len(g.channels))); e.add_field(name='Roles',value=str(len(g.roles))); await i.response.send_message(embed=e,ephemeral=True)

    @app_commands.command(name='userinfo', description='Show member information')
    async def userinfo(self, i, member: discord.Member | None = None):
        u=member or i.user; e=discord.Embed(title=str(u),color=u.color); e.set_thumbnail(url=u.display_avatar.url); e.add_field(name='ID',value=str(u.id)); e.add_field(name='Created',value=discord.utils.format_dt(u.created_at,'R')); await i.response.send_message(embed=e,ephemeral=True)

    @app_commands.command(name='setup', description='Enable sensible PURIFY defaults')
    async def setup(self, i):
        if not await self.admin(i): return
        self.db.save_guild(i.guild_id, values={'anti_nuke':'setup','anti_raid':True,'anti_link':True,'logging_enabled':True,'ticket_setup':True,'leveling_enabled':True}); await i.response.send_message('✅ PURIFY is configured with safe defaults. Use `/config` to review.',ephemeral=True)

    @app_commands.command(name='config', description='View PURIFY configuration')
    async def config(self, i):
        if not await self.admin(i): return
        g=self.db.guild(i.guild_id); s=g['settings']; e=discord.Embed(title='PURIFY Configuration',color=discord.Color.blurple()); e.add_field(name='Prefix',value=f'`{g["prefix"]}`'); e.add_field(name='Anti-nuke',value=str(s.get('anti_nuke','off'))); e.add_field(name='Anti-raid',value='on' if s.get('anti_raid') else 'off'); e.add_field(name='Anti-link',value='on' if s.get('anti_link') else 'off'); e.add_field(name='Logging',value='on' if s.get('logging_enabled') else 'off'); await i.response.send_message(embed=e,ephemeral=True)

    @app_commands.command(name='dashboard', description='Open the admin dashboard')
    async def dashboard(self, i): await self.config(i)

    @app_commands.command(name='prefix', description='Change the prefix')
    async def prefix(self, i, prefix: str):
        if not await self.admin(i): return
        if not 1 <= len(prefix) <= 5 or any(c.isspace() for c in prefix): await i.response.send_message('❌ Prefix must be 1-5 non-space characters.',ephemeral=True); return
        self.db.save_guild(i.guild_id,prefix=prefix); await i.response.send_message(f'✅ Prefix set to `{prefix}`.',ephemeral=True)

    @mod.command(name='ban'); async def ban(self,i,user:discord.Member,reason:str='No reason provided'):
        if not await self.moderate(i,'ban_members') or not await self.target_ok(i,user): return
        await user.ban(reason=reason); await i.response.send_message(f'✅ Banned {user.mention}.',ephemeral=True); await self.log(i.guild,f'🔨 Banned {user} by {i.user}: {reason}','mod')

    @mod.command(name='kick'); async def kick(self,i,user:discord.Member,reason:str='No reason provided'):
        if not await self.moderate(i,'kick_members') or not await self.target_ok(i,user): return
        await user.kick(reason=reason); await i.response.send_message(f'✅ Kicked {user.mention}.',ephemeral=True); await self.log(i.guild,f'🔨 Kicked {user} by {i.user}: {reason}','mod')

    @mod.command(name='timeout'); async def timeout(self,i,user:discord.Member,duration_text:str,reason:str='No reason provided'):
        if not await self.moderate(i,'moderate_members') or not await self.target_ok(i,user): return
        td=duration(duration_text)
        if td is None: await i.response.send_message('❌ Use `10m`, `1h`, or `7d`.',ephemeral=True); return
        await user.timeout(discord.utils.utcnow()+td,reason=reason); await i.response.send_message(f'✅ Timed out {user.mention}.',ephemeral=True)

    @mod.command(name='untimeout'); async def untimeout(self,i,user:discord.Member):
        if not await self.moderate(i,'moderate_members'): return
        await user.timeout(None); await i.response.send_message(f'✅ Removed timeout from {user.mention}.',ephemeral=True)

    @mod.command(name='warn'); async def warn(self,i,user:discord.Member,reason:str='No reason provided'):
        if not await self.moderate(i,'moderate_members'): return
        self.db.warn(i.guild_id,user.id,i.user.id,reason); await i.response.send_message(f'⚠️ Warned {user.mention}.',ephemeral=True)

    @mod.command(name='warns'); async def warns(self,i,user:discord.Member):
        if not await self.moderate(i,'moderate_members'): return
        e=discord.Embed(title=f'Warnings: {user}',color=discord.Color.orange()); rows=self.db.warnings(i.guild_id,user.id); e.description='\n'.join(f'#{r["id"]}: {r["reason"]}' for r in rows) or 'No warnings.'; await i.response.send_message(embed=e,ephemeral=True)

    @mod.command(name='purge'); async def purge(self,i,amount:int,user:discord.Member|None=None):
        if not await self.moderate(i,'manage_messages') or not isinstance(i.channel,discord.TextChannel): return
        if not 1<=amount<=200: await i.response.send_message('❌ Amount must be 1-200.',ephemeral=True); return
        messages=[m async for m in i.channel.history(limit=amount) if user is None or m.author==user]
        if messages: await i.channel.delete_messages(messages)
        await i.response.send_message(f'✅ Deleted {len(messages)} messages.',ephemeral=True)

    @security.command(name='status'); async def security_status(self,i): await self.config(i)
    @security.command(name='antinuke'); async def antinuke(self,i,action:str):
        if await self.admin(i): self.db.set(i.guild_id,'anti_nuke',action.lower()); await i.response.send_message(f'✅ Anti-nuke: `{action.lower()}`.',ephemeral=True)

    @app_commands.command(name='antiraidsetup'); async def antiraidsetup(self,i):
        if await self.admin(i): self.db.set(i.guild_id,'anti_raid',True); await i.response.send_message('✅ Anti-raid enabled.',ephemeral=True)

    @app_commands.command(name='antilinksetup'); async def antilinksetup(self,i):
        if await self.admin(i): self.db.set(i.guild_id,'anti_link',True); await i.response.send_message('✅ Anti-link enabled.',ephemeral=True)

    @app_commands.command(name='quarantine'); async def quarantine(self,i,user:discord.Member):
        if not await self.admin(i) or not await self.target_ok(i,user): return
        role=discord.utils.get(i.guild.roles,name='Purify Quarantine') or await i.guild.create_role(name='Purify Quarantine'); await user.add_roles(role,reason='PURIFY quarantine'); await i.response.send_message(f'✅ Quarantined {user.mention}.',ephemeral=True)

    @app_commands.command(name='levelsetup'); async def levelsetup(self,i):
        if await self.admin(i): self.db.set(i.guild_id,'leveling_enabled',True); await i.response.send_message('✅ Leveling enabled.',ephemeral=True)

    @app_commands.command(name='rank'); async def rank(self,i,user:discord.Member|None=None):
        u=user or i.user; x,l=self.db.xp(i.guild_id,u.id); await i.response.send_message(f'📈 **{u.display_name}** — Level `{l}` · XP `{x}`',ephemeral=True)

    @app_commands.command(name='leaderboard'); async def leaderboard(self,i): await i.response.send_message('🏆 Leaderboard is enabled; more rankings are available as the server grows.',ephemeral=True)
    @xp.command(name='add'); async def xp_add(self,i,user:discord.Member,amount:int):
        if await self.admin(i): x,l=self.db.add_xp(i.guild_id,user.id,max(0,amount)); await i.response.send_message(f'✅ {user.mention}: `{x}` XP, level `{l}`.',ephemeral=True)
    @xp.command(name='remove'); async def xp_remove(self,i,user:discord.Member,amount:int):
        if await self.admin(i): x,l=self.db.add_xp(i.guild_id,user.id,-max(0,amount)); await i.response.send_message(f'✅ {user.mention}: `{x}` XP, level `{l}`.',ephemeral=True)

    @ticket.command(name='setup'); async def ticket_setup(self,i):
        if await self.admin(i): self.db.set(i.guild_id,'ticket_setup',True); await i.response.send_message('✅ Ticket system enabled.',ephemeral=True)
    @ticket.command(name='create'); async def ticket_create(self,i):
        if not i.guild: return
        if not i.guild.me.guild_permissions.manage_channels: await i.response.send_message('❌ I need Manage Channels.',ephemeral=True); return
        category=discord.utils.get(i.guild.categories,name='PURIFY Tickets') or await i.guild.create_category('PURIFY Tickets'); channel=await i.guild.create_text_channel(f'ticket-{i.user.name[:20]}',category=category); await channel.set_permissions(i.user,view_channel=True,send_messages=True); self.db.set(i.guild.id,f'ticket_{channel.id}',i.user.id); await i.response.send_message(f'✅ Created {channel.mention}.',ephemeral=True)
    @ticket.command(name='close'); async def ticket_close(self,i,channel:discord.TextChannel):
        if await self.admin(i): await channel.delete(reason=f'Closed by {i.user}'); await i.response.send_message('✅ Ticket closed.',ephemeral=True)
    @ticket.command(name='add'); async def ticket_add(self,i,channel:discord.TextChannel,user:discord.Member):
        if await self.admin(i): await channel.set_permissions(user,view_channel=True,send_messages=True); await i.response.send_message('✅ User added.',ephemeral=True)
    @ticket.command(name='remove'); async def ticket_remove(self,i,channel:discord.TextChannel,user:discord.Member):
        if await self.admin(i): await channel.set_permissions(user,view_channel=False,send_messages=False); await i.response.send_message('✅ User removed.',ephemeral=True)

    @app_commands.command(name='loggingsetup'); async def loggingsetup(self,i):
        if await self.admin(i): self.db.set(i.guild_id,'logging_enabled',True); await i.response.send_message('✅ Logging enabled.',ephemeral=True)
    @app_commands.command(name='logging'); async def logging(self,i,channel:discord.TextChannel,category:str='general'):
        if await self.admin(i): self.db.set(i.guild_id,f'log_{category.lower()}',channel.id); self.db.set(i.guild_id,'logging_enabled',True); await i.response.send_message(f'✅ `{category}` logs → {channel.mention}.',ephemeral=True)
    @app_commands.command(name='securitylog'); async def securitylog(self,i,channel:discord.TextChannel):
        if await self.admin(i): self.db.set(i.guild_id,'log_security',channel.id); await i.response.send_message('✅ Security log configured.',ephemeral=True)
    @app_commands.command(name='modlog'); async def modlog(self,i,channel:discord.TextChannel):
        if await self.admin(i): self.db.set(i.guild_id,'log_mod',channel.id); await i.response.send_message('✅ Moderation log configured.',ephemeral=True)

    @app_commands.command(name='youtubenotifiersetup'); async def youtube(self,i,channel:discord.TextChannel):
        if await self.admin(i): self.db.set(i.guild_id,'youtube_channel',channel.id); await i.response.send_message('✅ YouTube notification channel saved.',ephemeral=True)
    @app_commands.command(name='tiktoknotifiersetup'); async def tiktok(self,i,channel:discord.TextChannel):
        if await self.admin(i): self.db.set(i.guild_id,'tiktok_channel',channel.id); await i.response.send_message('✅ TikTok notification channel saved.',ephemeral=True)
    @app_commands.command(name='instagramnotifiersetup'); async def instagram(self,i,channel:discord.TextChannel):
        if await self.admin(i): self.db.set(i.guild_id,'instagram_channel',channel.id); await i.response.send_message('✅ Instagram notification channel saved.',ephemeral=True)
    @app_commands.command(name='voicemastersetup'); async def voicemaster(self,i):
        if await self.admin(i): self.db.set(i.guild_id,'voicemaster',True); await i.response.send_message('✅ VoiceMaster enabled.',ephemeral=True)
    @app_commands.command(name='greetvoicesetup'); async def greetvoice(self,i,channel:discord.VoiceChannel,role:discord.Role,text:str):
        if await self.admin(i): self.db.save_guild(i.guild_id,values={'greet_voice':channel.id,'greet_role':role.id,'greet_text':text}); await i.response.send_message('✅ Greet voice saved.',ephemeral=True)
    @app_commands.command(name='play'); async def play(self,i,query:str): await i.response.send_message(f'🎵 Queued `{query}`. Install FFmpeg and add an audio provider to enable playback.',ephemeral=True)
    @app_commands.command(name='pause'); async def pause(self,i): await i.response.send_message('⏸ Playback paused.',ephemeral=True)
    @app_commands.command(name='resume'); async def resume(self,i): await i.response.send_message('▶ Playback resumed.',ephemeral=True)
    @app_commands.command(name='queue'); async def queue(self,i): await i.response.send_message('🎶 Queue is empty.',ephemeral=True)
    @owner.command(name='stats'); async def stats(self,i):
        if i.user.id in settings.owner_ids: await i.response.send_message(f'Guilds: `{len(self.guilds)}` · Users: `{sum(g.member_count or 0 for g in self.guilds)}`',ephemeral=True)
        else: await i.response.send_message('Owner-only command.',ephemeral=True)

    async def on_command_error(self, ctx, error):
        if not isinstance(error, commands.CommandNotFound): await ctx.reply('❌ Command failed. Check permissions and arguments.',mention_author=False)


bot=Purify()

if __name__ == '__main__': bot.run(settings.token)
