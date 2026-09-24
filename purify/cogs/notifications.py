from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Notifications(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="youtubenotifiersetup", description="Set a channel for YouTube alerts")
    @app_commands.describe(channel="Discord channel to send alerts to")
    async def youtubenotifiersetup(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can configure notifications.", ephemeral=True)
            return
        self.bot.db.set_setting(interaction.guild_id, "youtube_channel", channel.id)
        await interaction.response.send_message(f"✅ YouTube notifications configured for {channel.mention}.", ephemeral=True)

    @app_commands.command(name="tiktoknotifiersetup", description="Set a channel for TikTok alerts")
    @app_commands.describe(channel="Discord channel to send alerts to")
    async def tiktoknotifiersetup(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can configure notifications.", ephemeral=True)
            return
        self.bot.db.set_setting(interaction.guild_id, "tiktok_channel", channel.id)
        await interaction.response.send_message(f"✅ TikTok notifications configured for {channel.mention}.", ephemeral=True)

    @app_commands.command(name="instagramnotifiersetup", description="Set a channel for Instagram alerts")
    @app_commands.describe(channel="Discord channel to send alerts to")
    async def instagramnotifiersetup(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can configure notifications.", ephemeral=True)
            return
        self.bot.db.set_setting(interaction.guild_id, "instagram_channel", channel.id)
        await interaction.response.send_message(f"✅ Instagram notifications configured for {channel.mention}.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Notifications(bot))
