from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from urllib.parse import urlparse


class Database:
    """Small, dependency-free persistence layer for the lite deployment."""
    def __init__(self, url: str):
        self.path = self._path(url)
        if self.path != ':memory:':
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.executescript('''
            CREATE TABLE IF NOT EXISTS guilds (id INTEGER PRIMARY KEY, prefix TEXT NOT NULL DEFAULT '.', settings TEXT NOT NULL DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS warnings (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, user_id INTEGER, moderator_id INTEGER, reason TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS xp (guild_id INTEGER, user_id INTEGER, amount INTEGER NOT NULL DEFAULT 0, level INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(guild_id,user_id));
            CREATE TABLE IF NOT EXISTS tickets (channel_id INTEGER PRIMARY KEY, guild_id INTEGER, owner_id INTEGER, status TEXT NOT NULL DEFAULT 'open');
        ''')
        self.connection.commit()

    @staticmethod
    def _path(url: str) -> str:
        if not url.startswith('sqlite://'):
            return url
        parsed = urlparse(url)
        return parsed.path.lstrip('/') if parsed.path and parsed.path != '/:memory:' else ':memory:'

    def guild(self, guild_id: int) -> dict:
        row = self.connection.execute('SELECT * FROM guilds WHERE id=?', (guild_id,)).fetchone()
        if not row:
            return {'prefix': '.', 'settings': {}}
        return {'prefix': row['prefix'], 'settings': json.loads(row['settings'] or '{}')}

    def save_guild(self, guild_id: int, prefix: str | None = None, values: dict | None = None) -> None:
        current = self.guild(guild_id)
        merged = {**current['settings'], **(values or {})}
        self.connection.execute('''INSERT INTO guilds(id,prefix,settings) VALUES(?,?,?)
            ON CONFLICT(id) DO UPDATE SET prefix=excluded.prefix, settings=excluded.settings''',
            (guild_id, prefix or current['prefix'], json.dumps(merged, separators=(',', ':'))))
        self.connection.commit()

    def get(self, guild_id: int, key: str, default=None):
        return self.guild(guild_id)['settings'].get(key, default)

    def set(self, guild_id: int, key: str, value) -> None:
        self.save_guild(guild_id, values={key: value})

    def warn(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> None:
        self.connection.execute('INSERT INTO warnings(guild_id,user_id,moderator_id,reason) VALUES(?,?,?,?)', (guild_id, user_id, moderator_id, reason))
        self.connection.commit()

    def warnings(self, guild_id: int, user_id: int):
        return self.connection.execute('SELECT * FROM warnings WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 10', (guild_id, user_id)).fetchall()

    def xp(self, guild_id: int, user_id: int) -> tuple[int, int]:
        row = self.connection.execute('SELECT amount,level FROM xp WHERE guild_id=? AND user_id=?', (guild_id, user_id)).fetchone()
        return (int(row['amount']), int(row['level'])) if row else (0, 0)

    def add_xp(self, guild_id: int, user_id: int, amount: int) -> tuple[int, int]:
        old, _ = self.xp(guild_id, user_id)
        total = max(0, old + amount)
        level = total // 100
        self.connection.execute('''INSERT INTO xp(guild_id,user_id,amount,level) VALUES(?,?,?,?)
            ON CONFLICT(guild_id,user_id) DO UPDATE SET amount=excluded.amount,level=excluded.level''', (guild_id, user_id, total, level))
        self.connection.commit()
        return total, level

    def close(self) -> None:
        self.connection.close()
