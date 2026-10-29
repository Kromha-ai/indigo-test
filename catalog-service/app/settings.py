"""Settings read from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parent.parent


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    api_keys: tuple[str, ...]
    data_path: Path = SERVICE_ROOT / "data" / "catalog.json"
    public_base_url: str = "http://localhost:8000"
    rate_limit_per_minute: int = 120
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        if not self.api_keys:
            raise ConfigError("CATALOG_API_KEYS is empty: refusing to start without an API key")
        if self.rate_limit_per_minute < 1:
            raise ConfigError("RATE_LIMIT_PER_MINUTE must be at least 1")

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        keys = tuple(k.strip() for k in env.get("CATALOG_API_KEYS", "").split(",") if k.strip())
        data_path = Path(env.get("CATALOG_DATA_PATH", "data/catalog.json"))
        if not data_path.is_absolute():
            data_path = SERVICE_ROOT / data_path
        return cls(
            api_keys=keys,
            data_path=data_path,
            public_base_url=env.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/"),
            rate_limit_per_minute=int(env.get("RATE_LIMIT_PER_MINUTE", "120")),
            log_level=env.get("LOG_LEVEL", "INFO"),
        )
