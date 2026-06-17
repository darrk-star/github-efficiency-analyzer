from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    github_token: str | None = None
    github_api_base: str = "https://api.github.com"

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            github_token=os.getenv("GITHUB_TOKEN") or None,
            github_api_base=os.getenv("GITHUB_API_BASE", "https://api.github.com"),
        )
