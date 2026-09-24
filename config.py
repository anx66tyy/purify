from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _ids(value: str) -> set[int]:
    return {int(item.strip()) for item in value.split(',') if item.strip().isdigit()}


@dataclass(frozen=True, slots=True)
class Settings:
    token: str = os.getenv('DISCORD_TOKEN', '')
    database_url: str = os.getenv('DATABASE_URL', 'sqlite:///data/purify.db')
    prefix: str = os.getenv('BOT_PREFIX', '.')
    owner_ids: set[int] = _ids(os.getenv('OWNER_IDS', ''))
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')

    def validate(self) -> None:
        if not self.token:
            raise RuntimeError('DISCORD_TOKEN is required.')
        if not 1 <= len(self.prefix) <= 5 or any(char.isspace() for char in self.prefix):
            raise RuntimeError('BOT_PREFIX must contain 1-5 non-space characters.')


settings = Settings()
settings.validate()
