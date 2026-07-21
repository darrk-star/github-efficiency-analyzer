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
        return cls(
            github_token=os.getenv("GITHUB_TOKEN") or None,
            github_api_base=os.getenv("GITHUB_API_BASE", "https://api.github.com"),
            github_max_retries=int(os.getenv("GITHUB_MAX_RETRIES", "2")),
            github_retry_backoff_seconds=float(os.getenv("GITHUB_RETRY_BACKOFF_SECONDS", "0.25")),
        )
