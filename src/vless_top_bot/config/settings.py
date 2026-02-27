from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    default_top: int = 5
    default_attempts: int = 3
    default_timeout: float = 2.0
    default_fetch_timeout: float = 15.0
    default_concurrency: int = 50
    data_dir: str = "./data"


def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    return Settings(
        telegram_bot_token=token,
        default_top=int(os.getenv("DEFAULT_TOP", "5")),
        default_attempts=int(os.getenv("DEFAULT_ATTEMPTS", "3")),
        default_timeout=float(os.getenv("DEFAULT_TIMEOUT", "2.0")),
        default_fetch_timeout=float(os.getenv("DEFAULT_FETCH_TIMEOUT", "15.0")),
        default_concurrency=int(os.getenv("DEFAULT_CONCURRENCY", "50")),
        data_dir=os.getenv("DATA_DIR", "./data"),
    )
