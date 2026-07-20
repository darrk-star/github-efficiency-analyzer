from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


WorkflowOutcome = Literal["successful", "failed", "cancelled", "excluded"]


def workflow_outcome(conclusion: str | None) -> WorkflowOutcome:
    normalized = (conclusion or "").lower()
    if normalized == "success":
        return "successful"
    if normalized == "cancelled":
        return "cancelled"
    if normalized in {"neutral", "skipped", "stale", ""}:
        return "excluded"
    return "failed"


@dataclass(frozen=True)
class PullRequestRecord:
    number: int
    title: str
    author: str
    state: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    merged_at: datetime | None
    additions: int
    deletions: int
    changed_files: int
    review_comments: int
    comments: int
    commits: int
    reviewers: tuple[str, ...]
    url: str

    @property
    def is_merged(self) -> bool:
        return self.merged_at is not None


@dataclass(frozen=True)
class WorkflowRunRecord:
    id: int
    name: str
    event: str
    status: str
    conclusion: str | None
    created_at: datetime
    updated_at: datetime
    run_started_at: datetime | None
    actor: str
    branch: str
    duration_minutes: float | None
    html_url: str
    jobs_url: str
    failure_category: str
    failure_detail: str | None
    failure_source: str = "unknown"
