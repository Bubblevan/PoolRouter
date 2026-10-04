from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_local_env(path: Path | None = None) -> None:
    """Load missing settings from the repo .env without logging any values."""
    path = path or Path.cwd() / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    local_api_key: str
    groq_api_key: str = ""
    groq_account_tier: str = ""
    openrouter_api_key: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        load_local_env()
        return cls(
            local_api_key=os.getenv("POOLROUTER_API_KEY", ""),
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            groq_account_tier=os.getenv("GROQ_ACCOUNT_TIER", "").lower(),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        )
