from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="ping")
    async def ping_prefix(self, ctx: commands.Context) -> None:
        await ctx.reply(f"Pong! Latency: {round(self.bot.latency * 1000)}ms")

    @app_commands.command(name="ping")
    async def ping_slash(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"Pong! Latency: {round(self.bot.latency * 1000)}ms", ephemeral=True)

    @commands.command(name="help")
    async def help_prefix(self, ctx: commands.Context) -> None:
        embed = discord.Embed(title="PURIFY Help", description="Use /help for the main command dashboard.", color=discord.Color.blurple())
        embed.add_field(name="Security", value="/security status /antiraidsetup /antilinksetup")
        embed.add_field(name="Moderation", value="/mod ban /mod kick /mod warn /mod purge")
        embed.add_field(name="Utility", value="/ping /serverinfo /userinfo /config")
        await ctx.reply(embed=embed)

    @app_commands.command(name="help")
    async def help_slash(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(title="PURIFY Help", description="Main command dashboard", color=discord.Color.blurple())
        embed.add_field(name="🛡 Security", value="status, antinuke, antiraidsetup, antilinksetup")
        embed.add_field(name="🔨 Moderation", value="ban, kick, warn, purge")
        embed.add_field(name="⚙ Utility", value="ping, serverinfo, userinfo, config")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="serverinfo")
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return
        embed = discord.Embed(title=guild.name, color=discord.Color.blurple())
        embed.add_field(name="Members", value=str(guild.member_count))
        embed.add_field(name="Boosts", value=str(guild.premium_subscription_count or 0))
        embed.add_field(name="Owner", value=str(guild.owner))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="userinfo")
    @app_commands.describe(member="The user to inspect")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        embed = discord.Embed(title=f"User info: {target}", color=target.color)
        embed.add_field(name="ID", value=str(target.id))
        embed.add_field(name="Created", value=target.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"))
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))
