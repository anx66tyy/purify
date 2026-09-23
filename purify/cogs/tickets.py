from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    ticket = app_commands.Group(name="ticket", description="Ticket management")

    @ticket.command(name="setup")
    async def setup(self, interaction: discord.Interaction) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can set up ticketing.", ephemeral=True)
            return
        self.bot.db.set_setting(interaction.guild_id, "ticket_setup", True)
        await interaction.response.send_message("Ticket system is enabled and ready for channel creation.", ephemeral=True)

    @ticket.command(name="create")
    async def create(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        category = discord.utils.get(interaction.guild.categories, name="PURIFY Tickets")
        if category is None:
            category = await interaction.guild.create_category_channel("PURIFY Tickets")
        channel = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name.lower()}", category=category)
        self.bot.db.create_ticket(interaction.guild_id, interaction.user.id, channel.id)
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"Created support ticket: {channel.mention}", ephemeral=True)

    @ticket.command(name="close")
    @app_commands.describe(channel="Ticket channel to close")
    async def close(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can close tickets.", ephemeral=True)
            return
        self.bot.db.close_ticket(channel.id)
        await channel.send("This ticket has been closed by a moderator.")
        await interaction.response.send_message(f"Closed ticket {channel.mention}.", ephemeral=True)

    @ticket.command(name="add")
    @app_commands.describe(channel="Ticket channel", user="Member to add")
    async def add_user(self, interaction: discord.Interaction, channel: discord.TextChannel, user: discord.Member) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can add members to tickets.", ephemeral=True)
            return
        await channel.set_permissions(user, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"Added {user.mention} to {channel.mention}.", ephemeral=True)

    @ticket.command(name="remove")
    @app_commands.describe(channel="Ticket channel", user="Member to remove")
    async def remove_user(self, interaction: discord.Interaction, channel: discord.TextChannel, user: discord.Member) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can remove members from tickets.", ephemeral=True)
            return
        await channel.set_permissions(user, read_messages=False, send_messages=False)
        await interaction.response.send_message(f"Removed {user.mention} from {channel.mention}.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tickets(bot))
