from datetime import datetime, timezone

import pytest

from app.ci_failure_analysis import analyze_failure_log
from app.metrics import (
    build_daily_failure_trend,
    build_failed_workflow_breakdown,
    build_weekly_ci_digest,
    summarize_pull_requests,
    summarize_workflow_runs,
)
from app.models import PullRequestRecord, WorkflowRunRecord, workflow_outcome


def _dt(hour: int) -> datetime:
    return datetime(2026, 6, 1, hour, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("conclusion", "expected"),
    [
        ("success", "successful"),
        ("failure", "failed"),
        ("timed_out", "failed"),
        ("action_required", "failed"),
        ("cancelled", "cancelled"),
        ("neutral", "excluded"),
        ("skipped", "excluded"),
        ("stale", "excluded"),
        (None, "excluded"),
    ],
)
def test_workflow_outcome_groups_github_conclusions(conclusion, expected):
    assert workflow_outcome(conclusion) == expected


def test_summarize_pull_requests_handles_merged_and_open_records():
    records = [
        PullRequestRecord(
            number=1,
            title="Add cache",
            author="alice",
            state="closed",
            created_at=_dt(0),
            updated_at=_dt(3),
            closed_at=_dt(3),
            merged_at=_dt(3),
            additions=50,
            deletions=10,
            changed_files=3,
            review_comments=2,
            comments=1,
            commits=2,
            reviewers=("bob",),
            url="https://example.com/1",
        ),
        PullRequestRecord(
            number=2,
            title="Fix bug",
            author="alice",
            state="open",
            created_at=_dt(1),
            updated_at=_dt(2),
            closed_at=None,
            merged_at=None,
            additions=10,
            deletions=5,
            changed_files=1,
            review_comments=0,
            comments=2,
            commits=1,
            reviewers=(),
            url="https://example.com/2",
        ),
    ]

    summary = summarize_pull_requests(records)

    assert summary.total_prs == 2
    assert summary.merged_prs == 1
    assert summary.open_prs == 1
    assert summary.avg_merge_hours == 3.0
    assert summary.median_merge_hours == 3.0
    assert summary.avg_pr_size == 37.5
    assert summary.avg_changed_files == 2.0
    assert summary.avg_comments == 2.5
    assert summary.top_authors == [("alice", 2)]


def test_summarize_workflow_runs_groups_failures_and_success_rate():
    records = [
        WorkflowRunRecord(
            id=1,
            name="CI",
            event="pull_request",
            status="completed",
            conclusion="success",
            created_at=_dt(0),
            updated_at=_dt(1),
            run_started_at=_dt(0),
            actor="alice",
            branch="main",
            duration_minutes=60.0,
            html_url="https://example.com/runs/1",
            jobs_url="https://example.com/runs/1/jobs",
            failure_category="passed",
            failure_detail=None,
        ),
        WorkflowRunRecord(
            id=2,
            name="CI",
            event="pull_request",
            status="completed",
            conclusion="failure",
            created_at=_dt(2),
            updated_at=_dt(3),
            run_started_at=_dt(2),
            actor="bob",
            branch="feature/a",
            duration_minutes=45.0,
            html_url="https://example.com/runs/2",
            jobs_url="https://example.com/runs/2/jobs",
            failure_category="test_failure",
            failure_detail="Job 'tests' failed at step 'pytest'.",
        ),
        WorkflowRunRecord(
            id=3,
            name="Lint",
            event="push",
            status="completed",
            conclusion="cancelled",
            created_at=_dt(4),
            updated_at=_dt(5),
            run_started_at=_dt(4),
            actor="carol",
            branch="feature/b",
            duration_minutes=15.0,
            html_url="https://example.com/runs/3",
            jobs_url="https://example.com/runs/3/jobs",
            failure_category="cancelled",
            failure_detail="Workflow run was cancelled.",
        ),
    ]

    summary = summarize_workflow_runs(records)

    assert summary.total_runs == 3
    assert summary.successful_runs == 1
    assert summary.failed_runs == 1
    assert summary.cancelled_runs == 1
    assert summary.excluded_runs == 0
    assert summary.success_rate == 50.0
    assert summary.avg_duration_minutes == 40.0
    assert summary.failure_categories == [("test_failure", 1)]
    assert summary.top_failed_workflows == [("CI", 1)]


def test_summarize_workflow_runs_preserves_zero_success_rate():
    records = [
        WorkflowRunRecord(
            id=1,
            name="CI",
            event="pull_request",
            status="completed",
            conclusion="failure",
            created_at=_dt(0),
            updated_at=_dt(1),
            run_started_at=_dt(0),
            actor="alice",
            branch="main",
            duration_minutes=20.0,
            html_url="https://example.com/runs/1",
            jobs_url="https://example.com/runs/1/jobs",
            failure_category="test_failure",
            failure_detail="pytest failed",
        )
    ]

    summary = summarize_workflow_runs(records)

    assert summary.success_rate == 0.0


def test_analyze_failure_log_detects_dependency_failure():
    log = """
    Collecting package
    ERROR: Could not find a version that satisfies the requirement private-package==1.2.3
    ERROR: No matching distribution found for private-package==1.2.3
    """

    result = analyze_failure_log(log)

    assert result.category == "dependency_failure"
    assert result.detail == (
        "ERROR: Could not find a version that satisfies the requirement "
        "private-package==1.2.3"
    )


def test_analyze_failure_log_detects_permission_failure():
    log = """
    Run deploy
    cp: cannot create regular file '/var/www/app': Permission denied
    Error: Process completed with exit code 1.
    """

    result = analyze_failure_log(log)

    assert result.category == "permission_failure"
    assert "permission denied" in (result.detail or "").lower()


def test_generic_exit_code_does_not_claim_test_failure():
    result = analyze_failure_log("Error: Process completed with exit code 1")

    assert result.category == "unknown_failure"
    assert result.source == "fallback"


def test_build_weekly_ci_digest_aggregates_trends():
    records = [
        WorkflowRunRecord(
            id=1,
            name="CI",
            event="pull_request",
            status="completed",
            conclusion="failure",
            created_at=_dt(0),
            updated_at=_dt(1),
            run_started_at=_dt(0),
            actor="alice",
            branch="main",
            duration_minutes=20.0,
            html_url="https://example.com/runs/1",
            jobs_url="https://example.com/runs/1/jobs",
            failure_category="test_failure",
            failure_detail="pytest failed",
        ),
        WorkflowRunRecord(
            id=2,
            name="CI",
            event="pull_request",
            status="completed",
            conclusion="failure",
            created_at=_dt(0),
            updated_at=_dt(1),
            run_started_at=_dt(0),
            actor="bob",
            branch="main",
            duration_minutes=22.0,
            html_url="https://example.com/runs/2",
            jobs_url="https://example.com/runs/2/jobs",
            failure_category="test_failure",
            failure_detail="pytest failed",
        ),
        WorkflowRunRecord(
            id=3,
            name="Lint",
            event="push",
            status="completed",
            conclusion="failure",
            created_at=_dt(5),
            updated_at=_dt(6),
            run_started_at=_dt(5),
            actor="carol",
            branch="feature/x",
            duration_minutes=8.0,
            html_url="https://example.com/runs/3",
            jobs_url="https://example.com/runs/3/jobs",
            failure_category="lint_failure",
            failure_detail="ruff found 3 errors",
        ),
        WorkflowRunRecord(
            id=4,
            name="Deploy",
            event="push",
            status="completed",
            conclusion="success",
            created_at=_dt(7),
            updated_at=_dt(8),
            run_started_at=_dt(7),
            actor="dave",
            branch="main",
            duration_minutes=10.0,
            html_url="https://example.com/runs/4",
            jobs_url="https://example.com/runs/4/jobs",
            failure_category="passed",
            failure_detail=None,
        ),
    ]

    trend = build_daily_failure_trend(records)
    breakdown = build_failed_workflow_breakdown(records)
    digest = build_weekly_ci_digest(records)

    assert trend == [
        {"date": "2026-06-01", "failure_category": "lint_failure", "count": 1},
        {"date": "2026-06-01", "failure_category": "test_failure", "count": 2},
    ]
    assert [item["workflow"] for item in breakdown] == ["CI", "Lint"]
    assert digest.worst_day == ("2026-06-01", 3)
    assert digest.noisiest_category == ("test_failure", 2)
    assert digest.most_unstable_workflow == ("CI", 2)
    assert digest.top_failure_details[0] == ("pytest failed", 2)
    assert "dominant CI failure mode" in digest.key_risks[1]
    assert "flaky tests" in digest.recommended_actions[0].lower()
    assert digest.repeated_issue_commentary[0] == "Repeated issue (2x): pytest failed"
