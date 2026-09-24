from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from urllib.parse import urlparse


class Database:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.db_path = self._resolve_path(database_url)
        self._ensure_parent_directory()
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    def _resolve_path(self, database_url: str) -> str:
        if database_url.startswith("sqlite://"):
            parsed = urlparse(database_url)
            if parsed.path and parsed.path != ":memory:":
                return parsed.path.lstrip("/")
            return ":memory:"
        return database_url

    def _ensure_parent_directory(self) -> None:
        if self.db_path == ":memory:":
            return
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def init_schema(self) -> None:
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS guilds (
                    guild_id INTEGER PRIMARY KEY,
                    prefix TEXT DEFAULT '.',
                    settings TEXT DEFAULT '{}'
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    moderator_id INTEGER NOT NULL,
                    reason TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS xp (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'open',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def get_prefix(self, guild_id: int) -> str:
        row = self.conn.execute(
            "SELECT prefix FROM guilds WHERE guild_id = ?",
            (guild_id,),
        ).fetchone()
        if row is None:
            return "."
        return row["prefix"] or "."

    def set_prefix(self, guild_id: int, prefix: str) -> None:
        self.upsert_guild(guild_id, prefix=prefix)

    def get_guild(self, guild_id: int) -> dict:
        row = self.conn.execute(
            "SELECT prefix, settings FROM guilds WHERE guild_id = ?",
            (guild_id,),
        ).fetchone()
        settings = {}
        if row is not None:
            settings = json.loads(row["settings"] or "{}")
        return {"prefix": row["prefix"] if row else ".", "settings": settings}

    def upsert_guild(self, guild_id: int, prefix: str | None = None, settings: dict | None = None) -> None:
        current = self.get_guild(guild_id)
        merged = {**current["settings"], **(settings or {})}
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO guilds (guild_id, prefix, settings)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    prefix = excluded.prefix,
                    settings = excluded.settings
                """,
                (guild_id, prefix or current["prefix"] or ".", json.dumps(merged, separators=(",", ":"))),
            )

    def get_setting(self, guild_id: int, key: str, default=None):
        return self.get_guild(guild_id)["settings"].get(key, default)

    def set_setting(self, guild_id: int, key: str, value) -> None:
        guild = self.get_guild(guild_id)
        guild["settings"][key] = value
        self.upsert_guild(guild_id, settings=guild["settings"])

    def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
                (guild_id, user_id, moderator_id, reason),
            )

    def get_warnings(self, guild_id: int, user_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC",
            (guild_id, user_id),
        ).fetchall()

    def get_xp(self, guild_id: int, user_id: int) -> tuple[int, int]:
        row = self.conn.execute(
            "SELECT xp, level FROM xp WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ).fetchone()
        if row is None:
            return 0, 0
        return int(row["xp"]), int(row["level"])

    def add_xp(self, guild_id: int, user_id: int, amount: int) -> tuple[int, int]:
        current_xp, _ = self.get_xp(guild_id, user_id)
        new_xp = current_xp + amount
        new_level = new_xp // 100
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO xp (guild_id, user_id, xp, level)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET
                    xp = excluded.xp,
                    level = excluded.level
                """,
                (guild_id, user_id, new_xp, new_level),
            )
        return new_xp, new_level

    def create_ticket(self, guild_id: int, user_id: int, channel_id: int) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO tickets (guild_id, user_id, channel_id, status) VALUES (?, ?, ?, 'open')",
                (guild_id, user_id, channel_id),
            )

    def close_ticket(self, channel_id: int) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE tickets SET status = 'closed' WHERE channel_id = ?",
                (channel_id,),
            )

    def close(self) -> None:
        self.conn.close()
