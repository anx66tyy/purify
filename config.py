from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class Settings:
    token: str = field(default_factory=lambda: os.getenv("DISCORD_TOKEN", ""))
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///data/purify.db"))
    prefix: str = field(default_factory=lambda: os.getenv("BOT_PREFIX", "."))
    owner_ids: set[int] = field(default_factory=lambda: {
        int(x.strip()) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip()
    })
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    enable_tts: bool = field(default_factory=lambda: os.getenv("ENABLE_TTS", "true").lower() in {"1", "true", "yes", "on"})

    def validate(self) -> None:
        if not self.token:
            raise ValueError("DISCORD_TOKEN is required. Set it in your .env file.")


settings = Settings()
settings.validate()

__all__ = ["settings", "Settings"]
