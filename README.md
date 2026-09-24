# PURIFY Lite

A fast, simple, premium-feeling Discord moderation and security bot. The lite runtime keeps the active implementation in one bot file while retaining the previous modular source files in the repository for compatibility and future expansion.

## Railway

Deploy this repository as a worker service. Add:

```env
DISCORD_TOKEN=your_bot_token
DATABASE_URL=sqlite:///data/purify.db
BOT_PREFIX=.
OWNER_IDS=your_discord_user_id
LOG_LEVEL=INFO
```

The included Dockerfile runs `python bot.py`. For persistent SQLite data on Railway, attach a persistent volume mounted at `/app/data`, or use an external database before production scaling.

Enable the **Message Content** and **Server Members** privileged intents in the Discord Developer Portal. Give the bot only the permissions it needs; its moderation commands also verify role hierarchy.

## Quick setup

1. Invite PURIFY with `bot` and `applications.commands` scopes.
2. Run `/setup` as an administrator.
3. Use `/config` to inspect settings.
4. Configure logs with `/logging securitylog` and `/logging modlog`.
5. Use `/help` for grouped commands.

## Commands

- Utility: `/ping`, `/help`, `/serverinfo`, `/userinfo`
- Setup: `/setup`, `/config`, `/dashboard`, `/prefix`
- Moderation: `/mod ban`, `unban`, `kick`, `timeout`, `untimeout`, `warn`, `warns`, `purge`, `softban`
- Security: `/security status`, `/security antinuke`, `/antiraidsetup`, `/antilinksetup`, `/quarantine`
- Leveling: `/levelsetup`, `/rank`, `/leaderboard`, `/xp add`, `/xp remove`
- Tickets: `/ticket setup`, `create`, `close`, `add`, `remove`
- Logging: `/loggingsetup`, `/logging`, `/logging securitylog`, `/logging modlog`
- Notifications: `/youtubenotifiersetup`, `/tiktoknotifiersetup`, `/instagramnotifiersetup`
- Voice/music: `/voicemastersetup`, `/greetvoicesetup`, `/play`, `/pause`, `/resume`, `/queue`
- Owner: `/owner stats`

Prefix commands work with `.`, the configured prefix, and bot mentions: `.ping`, `!ping`, or `@Purify ping`.

## Security notes

PURIFY never logs tokens. Anti-link only targets Discord invites by default, staff are bypassed, and anti-spam uses conservative burst thresholds. Test permissions in a private server before enabling automated actions.
