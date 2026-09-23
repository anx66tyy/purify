from __future__ import annotations

import re
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def safe_prefix(prefix: str) -> str:
    prefix = prefix.strip()
    return prefix if prefix else "."


def looks_like_invite(text: str) -> bool:
    return bool(re.search(r"discord(?:app)?\.com/invite|discord\.gg/", text, flags=re.IGNORECASE))
