from __future__ import annotations

import discord


def can_manage_role(member: discord.Member, role: discord.Role) -> bool:
    bot_member = member.guild.me
    if bot_member is None:
        return False
    return role != member.guild.default_role and bot_member.top_role > role and member.top_role > role


def can_manage_member(actor: discord.Member, target: discord.Member) -> bool:
    bot_member = actor.guild.me
    if bot_member is None:
        return False
    return actor.top_role > target.top_role and bot_member.top_role > target.top_role
