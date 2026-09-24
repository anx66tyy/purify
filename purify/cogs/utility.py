from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="ping")
    async def ping_prefix(self, ctx: commands.Context) -> None:
        await ctx.reply(f"Pong! `{round(self.bot.latency * 1000)}ms`")

    @app_commands.command(name="ping", description="Check PURIFY latency")
    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"🏓 Pong! `{round(self.bot.latency * 1000)}ms`", ephemeral=True)

    @commands.command(name="help")
    async def help_prefix(self, ctx: commands.Context) -> None:
        await ctx.reply(embed=self.help_embed())

    @app_commands.command(name="help", description="Open the PURIFY command dashboard")
    async def help(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=self.help_embed(), ephemeral=True)

    def help_embed(self) -> discord.Embed:
        embed = discord.Embed(title="🛡️ PURIFY Help", description="Powerful systems, organized into simple command groups.", color=discord.Color.blurple())
        embed.add_field(name="🛡 Security", value="`/security status` · `/security antinuke` · `/antiraidsetup` · `/antilinksetup`", inline=False)
        embed.add_field(name="🔨 Moderation", value="`/mod ban` · `/mod kick` · `/mod timeout` · `/mod warn` · `/mod purge`", inline=False)
        embed.add_field(name="🎫 Tickets", value="`/ticket setup` · `/ticket create` · `/ticket close`", inline=False)
        embed.add_field(name="📈 Leveling", value="`/rank` · `/leaderboard` · `/xp add` · `/xp remove`", inline=False)
        embed.add_field(name="⚙ Configuration", value="`/config` · `/prefix` · `/loggingsetup`", inline=False)
        embed.set_footer(text="Use /config to keep setup simple.")
        return embed

    @app_commands.command(name="serverinfo", description="Show server information")
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return
        embed = discord.Embed(title=guild.name, color=discord.Color.blurple())
        embed.add_field(name="Members", value=str(guild.member_count))
        embed.add_field(name="Channels", value=str(len(guild.channels)))
        embed.add_field(name="Roles", value=str(len(guild.roles)))
        embed.add_field(name="Boosts", value=str(guild.premium_subscription_count or 0))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="userinfo", description="Show information about a member")
    @app_commands.describe(member="Member to inspect")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        embed = discord.Embed(title=f"User info: {target}", color=target.color)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="ID", value=str(target.id))
        embed.add_field(name="Joined", value=discord.utils.format_dt(target.joined_at, "R") if target.joined_at else "Unknown")
        embed.add_field(name="Created", value=discord.utils.format_dt(target.created_at, "R"))
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))
