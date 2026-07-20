from __future__ import annotations

import hashlib
import re


_TIMESTAMP = re.compile(r"\b\d{4}-\d{2}-\d{2}t\d{2}:\d{2}:\d{2}(?:\.\d+)?z\b")
_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
_WINDOWS_PATH = re.compile(r"\b[a-z]:\\(?:[^\s\\]+\\)+([^\s\\:]+)", re.IGNORECASE)
_UNIX_PATH = re.compile(r"/(?:[^\s/]+/)+([^\s/:]+)")
_LINE_NUMBER = re.compile(r"(?<=:)\d+\b")
_LONG_NUMBER = re.compile(r"\b\d{4,}\b")


def normalize_failure_detail(detail: str | None) -> str:
    normalized = " ".join((detail or "").lower().split())
    if not normalized:
        return "unknown"

    normalized = _TIMESTAMP.sub("{timestamp}", normalized)
    normalized = _UUID.sub("{uuid}", normalized)
    normalized = _WINDOWS_PATH.sub(r"{path}/\1", normalized)
    normalized = _UNIX_PATH.sub(r"{path}/\1", normalized)
    normalized = _LINE_NUMBER.sub("{line}", normalized)
    normalized = _LONG_NUMBER.sub("{number}", normalized)
    return normalized


def build_failure_fingerprint(category: str, detail: str | None) -> str:
    payload = f"{category.lower()}::{normalize_failure_detail(detail)}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"ci-failure-{digest}"
