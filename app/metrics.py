from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import TypedDict

from app.failure_fingerprint import build_failure_fingerprint, normalize_failure_detail
from app.models import PullRequestRecord, WorkflowRunRecord, workflow_outcome
from app.snapshots import FailureIssue, FailureObservation


@dataclass(frozen=True)
class PullRequestMetricsSummary:
    total_prs: int
    merged_prs: int
    open_prs: int
    avg_merge_hours: float | None
    median_merge_hours: float | None
    avg_pr_size: float | None
    avg_changed_files: float | None
    avg_comments: float | None
    top_authors: list[tuple[str, int]]


class _IssueData(TypedDict):
    category: str
    normalized_detail: str
    example_detail: str
    count: int
    workflows: set[str]
    first_seen: datetime
    last_seen: datetime


@dataclass(frozen=True)
class WorkflowMetricsSummary:
    total_runs: int
    successful_runs: int
    failed_runs: int
    cancelled_runs: int
    excluded_runs: int
    success_rate: float | None
    avg_duration_minutes: float | None
    failure_categories: list[tuple[str, int]]
    top_failed_workflows: list[tuple[str, int]]


@dataclass(frozen=True)
class WeeklyCiDigest:
    worst_day: tuple[str, int] | None
    noisiest_category: tuple[str, int] | None
    most_unstable_workflow: tuple[str, int] | None
    top_failure_details: list[tuple[str, int]]
    key_risks: list[str]
    recommended_actions: list[str]
    repeated_issue_commentary: list[str]


def build_pr_rows(records: list[PullRequestRecord]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record in records:
        merge_hours = None
        if record.merged_at:
            merge_hours = round((record.merged_at - record.created_at).total_seconds() / 3600, 2)

        rows.append(
            {
                "number": record.number,
                "title": record.title,
                "author": record.author,
                "state": record.state,
                "created_at": record.created_at.isoformat(),
                "updated_at": record.updated_at.isoformat(),
                "closed_at": record.closed_at.isoformat() if record.closed_at else None,
                "merged_at": record.merged_at.isoformat() if record.merged_at else None,
                "merge_hours": merge_hours,
                "additions": record.additions,
                "deletions": record.deletions,
                "total_changes": record.additions + record.deletions,
                "changed_files": record.changed_files,
                "review_comments": record.review_comments,
                "issue_comments": record.comments,
                "commits": record.commits,
                "reviewer_count": len(record.reviewers),
                "reviewers": ",".join(record.reviewers),
                "url": record.url,
            }
        )
    return rows


def summarize_pull_requests(records: list[PullRequestRecord]) -> PullRequestMetricsSummary:
    merged_records = [record for record in records if record.is_merged]
    merge_hours = [
        (record.merged_at - record.created_at).total_seconds() / 3600
        for record in merged_records
        if record.merged_at is not None
    ]
    pr_sizes = [record.additions + record.deletions for record in records]
    changed_files = [record.changed_files for record in records]
    comments = [record.comments + record.review_comments for record in records]

    author_counts: dict[str, int] = {}
    for record in records:
        author_counts[record.author] = author_counts.get(record.author, 0) + 1

    top_authors = sorted(author_counts.items(), key=lambda item: (-item[1], item[0].lower()))[:5]

    return PullRequestMetricsSummary(
        total_prs=len(records),
        merged_prs=len(merged_records),
        open_prs=sum(1 for record in records if record.state == "open"),
        avg_merge_hours=_average_or_none(merge_hours),
        median_merge_hours=_median_or_none(merge_hours),
        avg_pr_size=_average_or_none(pr_sizes),
        avg_changed_files=_average_or_none(changed_files),
        avg_comments=_average_or_none(comments),
        top_authors=top_authors,
    )


def build_workflow_rows(records: list[WorkflowRunRecord]) -> list[dict[str, object]]:
    return [
        {
            "id": record.id,
            "name": record.name,
            "event": record.event,
            "status": record.status,
            "conclusion": record.conclusion,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
            "run_started_at": record.run_started_at.isoformat() if record.run_started_at else None,
            "actor": record.actor,
            "branch": record.branch,
            "duration_minutes": record.duration_minutes,
            "failure_category": record.failure_category,
            "failure_detail": record.failure_detail,
            "failure_source": record.failure_source,
            "html_url": record.html_url,
            "jobs_url": record.jobs_url,
        }
        for record in records
    ]


def summarize_workflow_runs(records: list[WorkflowRunRecord]) -> WorkflowMetricsSummary:
    completed_records = [record for record in records if record.status == "completed"]
    outcomes = [workflow_outcome(record.conclusion) for record in completed_records]
    successful_count = outcomes.count("successful")
    failed_count = outcomes.count("failed")
    cancelled_count = outcomes.count("cancelled")
    excluded_count = outcomes.count("excluded")
    failed_runs = [
        record for record in completed_records if workflow_outcome(record.conclusion) == "failed"
    ]
    durations = [
        record.duration_minutes
        for record in completed_records
        if record.duration_minutes is not None
    ]

    category_counts: dict[str, int] = {}
    workflow_failures: dict[str, int] = {}
    for record in failed_runs:
        category_counts[record.failure_category] = (
            category_counts.get(record.failure_category, 0) + 1
        )
        workflow_failures[record.name] = workflow_failures.get(record.name, 0) + 1

    failure_categories = sorted(
        category_counts.items(), key=lambda item: (-item[1], item[0].lower())
    )

    top_failed_workflows = sorted(
        workflow_failures.items(), key=lambda item: (-item[1], item[0].lower())
    )[:5]

    success_rate = None
    denominator = successful_count + failed_count
    if denominator:
        success_rate = round(successful_count / denominator * 100, 2)

    return WorkflowMetricsSummary(
        total_runs=len(completed_records),
        successful_runs=successful_count,
        failed_runs=failed_count,
        cancelled_runs=cancelled_count,
        excluded_runs=excluded_count,
        success_rate=success_rate,
        avg_duration_minutes=_average_or_none(durations),
        failure_categories=failure_categories,
        top_failed_workflows=top_failed_workflows,
    )


def build_failure_issues(
    records: list[WorkflowRunRecord],
) -> tuple[list[FailureIssue], list[FailureObservation]]:
    issue_data: dict[str, _IssueData] = {}
    observations: list[FailureObservation] = []

    for record in sorted(records, key=lambda item: item.created_at):
        if record.status != "completed":
            continue

        outcome = workflow_outcome(record.conclusion)
        if outcome == "successful":
            observations.append(
                FailureObservation(
                    observed_at=record.created_at,
                    workflow=record.name,
                    outcome="success",
                    fingerprint=None,
                )
            )
            continue
        if outcome != "failed":
            continue

        fingerprint = build_failure_fingerprint(
            record.failure_category,
            record.failure_detail,
        )
        observations.append(
            FailureObservation(
                observed_at=record.created_at,
                workflow=record.name,
                outcome="failed",
                fingerprint=fingerprint,
            )
        )
        data = issue_data.setdefault(
            fingerprint,
            {
                "category": record.failure_category,
                "normalized_detail": normalize_failure_detail(record.failure_detail),
                "example_detail": record.failure_detail or "Unknown failure",
                "count": 0,
                "workflows": set(),
                "first_seen": record.created_at,
                "last_seen": record.created_at,
            },
        )
        data["count"] = int(data["count"]) + 1
        workflows = data["workflows"]
        if isinstance(workflows, set):
            workflows.add(record.name)
        data["first_seen"] = min(data["first_seen"], record.created_at)
        data["last_seen"] = max(data["last_seen"], record.created_at)

    issues = [
        FailureIssue(
            fingerprint=fingerprint,
            category=str(data["category"]),
            normalized_detail=str(data["normalized_detail"]),
            example_detail=str(data["example_detail"]),
            count=int(data["count"]),
            workflows=sorted(str(item) for item in data["workflows"]),
            first_seen=data["first_seen"],
            last_seen=data["last_seen"],
        )
        for fingerprint, data in issue_data.items()
    ]
    issues.sort(key=lambda item: (-item.count, item.fingerprint))
    return issues, observations


def build_daily_failure_trend(records: list[WorkflowRunRecord]):
    failed_records = [
        record
        for record in records
        if record.status == "completed" and workflow_outcome(record.conclusion) == "failed"
    ]

    if not failed_records:
        return []

    grouped: dict[tuple[str, str], int] = {}
    for record in failed_records:
        key = (record.created_at.date().isoformat(), record.failure_category)
        grouped[key] = grouped.get(key, 0) + 1

    return [
        {"date": date, "failure_category": category, "count": count}
        for (date, category), count in sorted(grouped.items(), key=lambda item: item[0])
    ]


def build_failed_workflow_breakdown(records: list[WorkflowRunRecord]):
    failed_records = [
        record
        for record in records
        if record.status == "completed" and workflow_outcome(record.conclusion) == "failed"
    ]
    if not failed_records:
        return []

    grouped: dict[str, int] = {}
    for record in failed_records:
        grouped[record.name] = grouped.get(record.name, 0) + 1

    return [
        {"workflow": workflow, "count": count}
        for workflow, count in sorted(grouped.items(), key=lambda item: (-item[1], item[0].lower()))
    ]


def build_weekly_ci_digest(records: list[WorkflowRunRecord]) -> WeeklyCiDigest:
    trend_frame = build_daily_failure_trend(records)
    workflow_frame = build_failed_workflow_breakdown(records)

    worst_day = None
    if trend_frame:
        daily_totals: dict[str, int] = {}
        for item in trend_frame:
            daily_totals[item["date"]] = daily_totals.get(item["date"], 0) + int(item["count"])
        first = sorted(daily_totals.items(), key=lambda item: (-item[1], item[0]))[0]
        worst_day = (str(first[0]), int(first[1]))

    category_counts: dict[str, int] = {}
    detail_counts: dict[str, int] = {}
    for record in records:
        if record.status != "completed" or workflow_outcome(record.conclusion) != "failed":
            continue
        category_counts[record.failure_category] = (
            category_counts.get(record.failure_category, 0) + 1
        )
        if record.failure_detail:
            detail_counts[record.failure_detail] = detail_counts.get(record.failure_detail, 0) + 1

    noisiest_category = None
    if category_counts:
        noisiest_category = sorted(
            category_counts.items(), key=lambda item: (-item[1], item[0].lower())
        )[0]

    most_unstable_workflow = None
    if workflow_frame:
        first = workflow_frame[0]
        most_unstable_workflow = (str(first["workflow"]), int(first["count"]))

    top_failure_details = sorted(
        detail_counts.items(), key=lambda item: (-item[1], item[0].lower())
    )[:5]

    key_risks: list[str] = []
    recommended_actions: list[str] = []
    repeated_issue_commentary: list[str] = []

    total_failures = sum(category_counts.values())
    if worst_day is not None and total_failures:
        worst_day_ratio = round(worst_day[1] / total_failures * 100, 2)
        key_risks.append(
            f"Failure volume concentrated on {worst_day[0]}, which accounts for "
            f"{worst_day_ratio}% of failed runs."
        )

    if noisiest_category is not None and total_failures:
        category_ratio = round(noisiest_category[1] / total_failures * 100, 2)
        key_risks.append(
            f"{noisiest_category[0]} is the dominant CI failure mode at "
            f"{category_ratio}% of failed runs."
        )
        recommended_actions.append(_recommend_action_for_category(noisiest_category[0]))

    if most_unstable_workflow is not None:
        key_risks.append(
            f"Workflow '{most_unstable_workflow[0]}' is the main source of instability with "
            f"{most_unstable_workflow[1]} failed runs."
        )
        recommended_actions.append(
            f"Review the owner and recent changes for workflow "
            f"'{most_unstable_workflow[0]}' and prioritize a stabilization pass."
        )

    for detail, count in top_failure_details[:3]:
        repeated_issue_commentary.append(f"Repeated issue ({count}x): {detail}")

    if not recommended_actions and total_failures == 0:
        recommended_actions.append(
            "CI remained stable in this window; keep monitoring for regressions rather than "
            "introducing new process changes."
        )

    recommended_actions = _deduplicate_preserve_order(recommended_actions)

    return WeeklyCiDigest(
        worst_day=worst_day,
        noisiest_category=noisiest_category,
        most_unstable_workflow=most_unstable_workflow,
        top_failure_details=top_failure_details,
        key_risks=key_risks,
        recommended_actions=recommended_actions,
        repeated_issue_commentary=repeated_issue_commentary,
    )


def _average_or_none(values: Sequence[int | float]) -> float | None:
    return round(mean(values), 2) if values else None


def _median_or_none(values: Sequence[int | float]) -> float | None:
    return round(median(values), 2) if values else None


def write_rows_to_csv(output_path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        output_path.write_text("", encoding="utf-8")
        return

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _recommend_action_for_category(category: str) -> str:
    category_actions = {
        "test_failure": (
            "Audit flaky tests, quarantine unstable cases, and tighten pre-merge test ownership."
        ),
        "lint_failure": (
            "Shift lint checks left with local pre-commit hooks or editor integration to reduce "
            "avoidable CI noise."
        ),
        "build_failure": (
            "Check recent build config or dependency changes and verify that build steps are "
            "reproducible locally."
        ),
        "dependency_failure": (
            "Pin dependency versions and add lockfile validation to reduce install drift across "
            "runs."
        ),
        "infra_failure": (
            "Review runner, network, and external service reliability; separate platform "
            "instability from code regressions."
        ),
        "permission_failure": (
            "Recheck credentials, token scopes, and deployment permissions for the affected "
            "workflow path."
        ),
        "resource_failure": (
            "Inspect memory and CPU pressure on runners and split oversized jobs where possible."
        ),
        "timeout": (
            "Break long-running jobs into smaller stages or cache expensive steps to reduce "
            "timeout risk."
        ),
        "unknown_failure": (
            "Inspect raw CI logs for the top failing workflow and add a new classification rule "
            "for the recurring pattern."
        ),
    }
    return category_actions.get(
        category,
        "Inspect the top failing runs in detail and turn the dominant pattern into a concrete "
        "remediation item.",
    )


def _deduplicate_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
