"""Settings read from the environment."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

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
        api_keys = tuple(k.strip() for k in env.get("CATALOG_API_KEYS", "").split(",") if k.strip())
        overrides: _Overrides = {}
        if "CATALOG_DATA_PATH" in env:
            data_path = Path(env["CATALOG_DATA_PATH"])
            overrides["data_path"] = (
                data_path if data_path.is_absolute() else SERVICE_ROOT / data_path
            )
        if "PUBLIC_BASE_URL" in env:
            overrides["public_base_url"] = env["PUBLIC_BASE_URL"].rstrip("/")
        if "RATE_LIMIT_PER_MINUTE" in env:
            try:
                overrides["rate_limit_per_minute"] = int(env["RATE_LIMIT_PER_MINUTE"])
            except ValueError as error:
                raise ConfigError("RATE_LIMIT_PER_MINUTE must be an integer") from error
        if "LOG_LEVEL" in env:
            overrides["log_level"] = env["LOG_LEVEL"]
        return cls(api_keys=api_keys, **overrides)


class _Overrides(TypedDict, total=False):
    """The optional `Settings` fields, as set from the environment."""

    data_path: Path
    public_base_url: str
    rate_limit_per_minute: int
    log_level: str
