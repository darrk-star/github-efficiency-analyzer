from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FailureAnalysis:
    category: str
    detail: str | None
    source: str


def analyze_failure_log(log_text: str, fallback_detail: str | None = None) -> FailureAnalysis:
    normalized = " ".join(log_text.lower().split())

    patterns: list[tuple[str, list[str]]] = [
        (
            "dependency_failure",
            [
                "no matching distribution found",
                "could not find a version that satisfies the requirement",
                "failed building wheel",
                "poetry could not find",
                "resolutionimpossible",
                "npm err! code eresolve",
            ],
        ),
        (
            "permission_failure",
            [
                "permission denied",
                "access is denied",
                "forbidden",
                "http 403",
                "unauthorized",
                "not permitted",
            ],
        ),
        (
            "infra_failure",
            [
                "failed to connect",
                "connection reset",
                "connection refused",
                "temporary failure in name resolution",
                "network is unreachable",
                "service unavailable",
                "timed out while waiting",
            ],
        ),
        (
            "build_failure",
            [
                "build failed",
                "compilation failed",
                "error: linker command failed",
                "module not found",
                "unable to compile",
                "syntaxerror:",
            ],
        ),
        (
            "lint_failure",
            [
                "ruff found",
                "flake8",
                "black would reformat",
                "isort found",
                "mypy found",
                "eslint found",
                "lint failed",
            ],
        ),
        (
            "test_failure",
            [
                "assertionerror",
                "failed: ",
                "test failed",
                "1 failed",
                "2 failed",
                "3 failed",
                "failures:",
            ],
        ),
    ]

    for category, keywords in patterns:
        if any(keyword in normalized for keyword in keywords):
            return FailureAnalysis(
                category=category,
                detail=_extract_first_matching_detail(log_text, keywords),
                source="logs",
            )

    if re.search(r"exit code\s+137|killed", normalized):
        return FailureAnalysis(
            category="resource_failure",
            detail=_extract_detail(log_text, "exit code"),
            source="logs",
        )

    if re.search(r"timed out|time limit exceeded", normalized):
        return FailureAnalysis(
            category="timeout",
            detail=_extract_detail(log_text, "timed out"),
            source="logs",
        )

    return FailureAnalysis(
        category="unknown_failure",
        detail=fallback_detail or _extract_first_error(log_text),
        source="fallback",
    )


def _extract_detail(log_text: str, keyword: str) -> str | None:
    lines = log_text.splitlines()
    keyword_lower = keyword.lower()
    for line in lines:
        if keyword_lower in line.lower():
            return line.strip()[:300]
    return _extract_first_error(log_text)


def _extract_first_matching_detail(log_text: str, keywords: list[str]) -> str | None:
    for line in log_text.splitlines():
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            return line.strip()[:300]
    return _extract_first_error(log_text)


def _extract_first_error(log_text: str) -> str | None:
    for line in log_text.splitlines():
        lowered = line.lower()
        if any(token in lowered for token in ("error", "failed", "exception", "denied")):
            return line.strip()[:300]
    return None
