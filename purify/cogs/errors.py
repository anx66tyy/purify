from __future__ import annotations

import traceback

import discord
from discord.ext import commands

from purify.core.logger import logger


class ErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandNotFound):
            return
        original = getattr(error, "original", error)
        logger.error("Prefix command error: %s\n%s", original, "".join(traceback.format_exception(original)))
        await ctx.reply("❌ PURIFY could not complete that command. Check permissions and arguments, then try again.", mention_author=False)

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError) -> None:
        original = getattr(error, "original", error)
        logger.error("Slash command error: %s\n%s", original, "".join(traceback.format_exception(original)))
        msg = "❌ PURIFY could not complete that command. Check permissions and configuration, then try again."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ErrorHandler(bot))
