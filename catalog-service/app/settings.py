"""Settings read from the environment."""

from __future__ import annotations

import os
from collections.abc import Mapping
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
    rate_limit_per_minute: int = 600
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        if not self.api_keys:
            raise ConfigError("CATALOG_API_KEYS is empty: refusing to start without an API key")
        if self.rate_limit_per_minute < 1:
            raise ConfigError("RATE_LIMIT_PER_MINUTE must be at least 1")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        """Read the variables that are set; anything missing keeps the field's default."""
        env = os.environ if env is None else env
        kwargs: dict[str, object] = {
            "api_keys": tuple(
                k.strip() for k in env.get("CATALOG_API_KEYS", "").split(",") if k.strip()
            )
        }
        if "CATALOG_DATA_PATH" in env:
            data_path = Path(env["CATALOG_DATA_PATH"])
            kwargs["data_path"] = data_path if data_path.is_absolute() else SERVICE_ROOT / data_path
        if "PUBLIC_BASE_URL" in env:
            kwargs["public_base_url"] = env["PUBLIC_BASE_URL"].rstrip("/")
        if "RATE_LIMIT_PER_MINUTE" in env:
            kwargs["rate_limit_per_minute"] = int(env["RATE_LIMIT_PER_MINUTE"])
        if "LOG_LEVEL" in env:
            kwargs["log_level"] = env["LOG_LEVEL"]
        return cls(**kwargs)
