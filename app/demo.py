from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.charts import write_failed_workflow_chart, write_failure_trend_chart
from app.html_report import write_html_report
from app.metrics import (
    build_daily_failure_trend,
    build_failed_workflow_breakdown,
    build_failure_issues,
    build_pr_rows,
    build_weekly_ci_digest,
    build_workflow_rows,
    summarize_pull_requests,
    summarize_workflow_runs,
    write_rows_to_csv,
)
from app.models import PullRequestRecord, WorkflowRunRecord
from app.report import write_markdown_report, write_weekly_digest_report
from app.snapshots import Snapshot, write_snapshot
from app.trends import compare_snapshots

DEFAULT_FIXTURE_PATH = Path("examples/fixtures/portfolio_demo.json")
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DemoFixture:
    repo: str
    days: int
    previous_generated_at: datetime
    current_generated_at: datetime
    pull_requests: list[PullRequestRecord]
    previous_workflow_runs: list[WorkflowRunRecord]
    current_workflow_runs: list[WorkflowRunRecord]


def load_demo_fixture(path: Path = DEFAULT_FIXTURE_PATH) -> DemoFixture:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DemoFixture(
        repo=str(payload["repo"]),
        days=int(payload["days"]),
        previous_generated_at=_parse_datetime(str(payload["previous_generated_at"])),
        current_generated_at=_parse_datetime(str(payload["current_generated_at"])),
        pull_requests=[_parse_pull_request(item) for item in payload["pull_requests"]],
        previous_workflow_runs=[
            _parse_workflow_run(item) for item in payload["previous_workflow_runs"]
        ],
        current_workflow_runs=[
            _parse_workflow_run(item) for item in payload["current_workflow_runs"]
        ],
    )


def run_demo(output_dir: Path, snapshot_dir: Path) -> tuple[str, list[Path]]:
    fixture = load_demo_fixture()
    output_dir.mkdir(parents=True, exist_ok=True)

    previous_snapshot = _build_snapshot(
        fixture.repo,
        fixture.days,
        fixture.previous_generated_at,
        fixture.previous_workflow_runs,
    )
    current_snapshot = _build_snapshot(
        fixture.repo,
        fixture.days,
        fixture.current_generated_at,
        fixture.current_workflow_runs,
    )
    comparison = compare_snapshots(previous_snapshot, current_snapshot)

    pr_summary = summarize_pull_requests(fixture.pull_requests)
    workflow_summary = summarize_workflow_runs(fixture.current_workflow_runs)
    pr_rows = build_pr_rows(fixture.pull_requests)
    workflow_rows = build_workflow_rows(fixture.current_workflow_runs)
    weekly_digest = build_weekly_ci_digest(fixture.current_workflow_runs)
    daily_trend_frame = build_daily_failure_trend(fixture.current_workflow_runs)
    failed_workflow_frame = build_failed_workflow_breakdown(fixture.current_workflow_runs)

    pr_csv_path = output_dir / "pull_requests.csv"
    workflow_csv_path = output_dir / "workflow_runs.csv"
    summary_path = output_dir / "summary.md"
    weekly_path = output_dir / "weekly_digest.md"
    html_path = output_dir / "index.html"
    trend_chart_path = output_dir / "ci_failure_trend.png"
    workflow_chart_path = output_dir / "unstable_workflows.png"

    previous_snapshot_path = write_snapshot(snapshot_dir, previous_snapshot)
    current_snapshot_path = write_snapshot(snapshot_dir, current_snapshot)
    write_rows_to_csv(pr_csv_path, pr_rows)
    write_rows_to_csv(workflow_csv_path, workflow_rows)
    write_markdown_report(summary_path, fixture.repo, fixture.days, pr_summary, workflow_summary)
    write_weekly_digest_report(weekly_path, fixture.repo, fixture.days, weekly_digest, comparison)
    chart_paths: list[Path] = []
    chart_jobs: list[tuple[Callable[[Any, Path], bool], Any, Path]] = [
        (write_failure_trend_chart, daily_trend_frame, trend_chart_path),
        (write_failed_workflow_chart, failed_workflow_frame, workflow_chart_path),
    ]
    for chart_fn, chart_data, chart_path in chart_jobs:
        try:
            chart_written = chart_fn(chart_data, chart_path)
        except (OSError, RuntimeError) as exc:
            LOGGER.debug("Skipping optional demo chart %s: %s", chart_path, exc)
            chart_written = False
        if chart_written:
            chart_paths.append(chart_path)

    artifact_links: dict[str, Path] = {
        "Pull request CSV": _relative_to_output(pr_csv_path, output_dir),
        "Workflow CSV": _relative_to_output(workflow_csv_path, output_dir),
        "Markdown summary": _relative_to_output(summary_path, output_dir),
        "Weekly digest": _relative_to_output(weekly_path, output_dir),
        "Previous snapshot": _relative_to_output(previous_snapshot_path, output_dir),
        "Current snapshot": _relative_to_output(current_snapshot_path, output_dir),
    }
    for chart_path in chart_paths:
        artifact_links[chart_path.stem.replace("_", " ").title()] = _relative_to_output(
            chart_path,
            output_dir,
        )

    write_html_report(
        html_path,
        fixture.repo,
        fixture.days,
        pr_summary,
        workflow_summary,
        weekly_digest,
        comparison,
        artifact_links,
    )

    written_paths = [
        pr_csv_path,
        workflow_csv_path,
        summary_path,
        weekly_path,
        html_path,
        previous_snapshot_path,
        current_snapshot_path,
        *chart_paths,
    ]
    return fixture.repo, written_paths


def _build_snapshot(
    repo: str,
    days: int,
    generated_at: datetime,
    records: list[WorkflowRunRecord],
) -> Snapshot:
    summary = summarize_workflow_runs(records)
    issues, observations = build_failure_issues(records)
    return Snapshot(
        schema_version=1,
        repo=repo,
        window_days=days,
        generated_at=generated_at,
        total_runs=summary.total_runs,
        failed_runs=summary.failed_runs,
        issues=issues,
        observations=observations,
    )


def _parse_pull_request(item: dict[str, Any]) -> PullRequestRecord:
    return PullRequestRecord(
        number=int(item["number"]),
        title=str(item["title"]),
        author=str(item["author"]),
        state=str(item["state"]),
        created_at=_parse_datetime(str(item["created_at"])),
        updated_at=_parse_datetime(str(item["updated_at"])),
        closed_at=_parse_optional_datetime(item.get("closed_at")),
        merged_at=_parse_optional_datetime(item.get("merged_at")),
        additions=int(item["additions"]),
        deletions=int(item["deletions"]),
        changed_files=int(item["changed_files"]),
        review_comments=int(item["review_comments"]),
        comments=int(item["comments"]),
        commits=int(item["commits"]),
        reviewers=tuple(str(value) for value in item["reviewers"]),
        url=str(item["url"]),
    )


def _parse_workflow_run(item: dict[str, Any]) -> WorkflowRunRecord:
    return WorkflowRunRecord(
        id=int(item["id"]),
        name=str(item["name"]),
        event=str(item["event"]),
        status=str(item["status"]),
        conclusion=str(item["conclusion"]) if item["conclusion"] is not None else None,
        created_at=_parse_datetime(str(item["created_at"])),
        updated_at=_parse_datetime(str(item["updated_at"])),
        run_started_at=_parse_optional_datetime(item.get("run_started_at")),
        actor=str(item["actor"]),
        branch=str(item["branch"]),
        duration_minutes=(
            float(item["duration_minutes"]) if item["duration_minutes"] is not None else None
        ),
        html_url=str(item["html_url"]),
        jobs_url=str(item["jobs_url"]),
        failure_category=str(item["failure_category"]),
        failure_detail=(
            str(item["failure_detail"]) if item["failure_detail"] is not None else None
        ),
        failure_source="fixture",
    )


def _parse_optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    return _parse_datetime(str(value))


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _relative_to_output(path: Path, output_dir: Path) -> Path:
    return Path(os.path.relpath(path.resolve(), output_dir.resolve()))
