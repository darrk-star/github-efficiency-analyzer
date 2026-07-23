from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    github_token: str | None = None
    github_api_base: str = "https://api.github.com"
    github_max_retries: int = 2
    github_retry_backoff_seconds: float = 0.25

    @classmethod
    def from_env(cls) -> AppConfig:
        retry_count = _non_negative_int_env("GITHUB_MAX_RETRIES", "2")
        return cls(
            github_token=os.getenv("GITHUB_TOKEN") or None,
            github_api_base=os.getenv("GITHUB_API_BASE", "https://api.github.com"),
            github_max_retries=retry_count,
            github_retry_backoff_seconds=float(os.getenv("GITHUB_RETRY_BACKOFF_SECONDS", "0.25")),
        )


def _non_negative_int_env(name: str, default: str) -> int:
    raw_value = os.getenv(name, default)
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a non-negative integer") from exc
    if value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value
