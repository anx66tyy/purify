from __future__ import annotations

import discord


def is_owner(user: discord.User, owner_ids: set[int]) -> bool:
    return user.id in owner_ids


async def require_admin(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return False
    if interaction.user.guild_permissions.administrator:
        return True
    await interaction.response.send_message("This command requires administrator permission.", ephemeral=True)
    return False


async def require_moderator(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return False
    perms = interaction.user.guild_permissions
    if perms.administrator or perms.moderate_members or perms.manage_messages:
        return True
    await interaction.response.send_message("This command requires moderator permissions.", ephemeral=True)
    return False
