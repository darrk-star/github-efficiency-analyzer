from __future__ import annotations

from pathlib import Path

from app.html_report import write_html_report
from app.metrics import (
    PullRequestMetricsSummary,
    WeeklyCiDigest,
    WorkflowMetricsSummary,
)
from app.trends import TrendComparison, TrendIssue


def test_write_html_report_renders_metrics_statuses_and_artifact_links(tmp_path):
    output_path = tmp_path / "index.html"

    write_html_report(
        output_path=output_path,
        repo="owner/repo",
        days=14,
        pr_summary=PullRequestMetricsSummary(
            total_prs=8,
            merged_prs=5,
            open_prs=3,
            avg_merge_hours=6.5,
            median_merge_hours=4.0,
            avg_pr_size=120.0,
            avg_changed_files=4.5,
            avg_comments=2.0,
            top_authors=[("alice", 5), ("bob", 3)],
        ),
        workflow_summary=WorkflowMetricsSummary(
            total_runs=20,
            successful_runs=14,
            failed_runs=5,
            cancelled_runs=1,
            excluded_runs=0,
            success_rate=73.68,
            avg_duration_minutes=9.25,
            failure_categories=[("test_failure", 3), ("build_failure", 2)],
            top_failed_workflows=[("CI", 4), ("Release", 1)],
        ),
        digest=WeeklyCiDigest(
            worst_day=("2026-07-20", 3),
            noisiest_category=("test_failure", 3),
            most_unstable_workflow=("CI", 4),
            top_failure_details=[("pytest failed", 3)],
            key_risks=["CI has repeated test failures."],
            recommended_actions=["Stabilize the flaky checkout test."],
            repeated_issue_commentary=["`regressed`: test_failure (3 occurrences) - pytest failed"],
        ),
        comparison=TrendComparison(
            baseline_available=True,
            issues=[
                TrendIssue(
                    fingerprint="ci-failure-abc123",
                    category="test_failure",
                    status="regressed",
                    current_count=3,
                    previous_count=1,
                    workflows=["CI"],
                    example_detail="pytest failed <danger>",
                    suspected_flaky=True,
                    transition_count=1,
                ),
                TrendIssue(
                    fingerprint="ci-failure-def456",
                    category="build_failure",
                    status="resolved",
                    current_count=0,
                    previous_count=2,
                    workflows=["Release"],
                    example_detail="npm build failed",
                    suspected_flaky=False,
                    transition_count=0,
                ),
            ],
        ),
        artifact_links={
            "Pull request CSV": Path("pull_requests.csv"),
            "Workflow CSV": Path("workflow_runs.csv"),
            "Markdown summary": Path("summary.md"),
            "Weekly digest": Path("weekly_digest.md"),
            "Failure trend chart": Path("ci_failure_trend.png"),
            "Snapshot": Path("snapshots/owner__repo__14__2026-07-20.json"),
        },
    )

    html = output_path.read_text(encoding="utf-8")
    assert "<!doctype html>" in html
    assert "owner/repo" in html
    assert "Pull Request Metrics" in html
    assert "Workflow success rate" in html
    assert "Recurring CI Issues" in html
    assert "regressed" in html
    assert "suspected flaky" in html
    assert "resolved" in html
    assert "pytest failed &lt;danger&gt;" in html
    assert 'href="pull_requests.csv"' in html
    assert 'src="ci_failure_trend.png"' in html


def test_write_html_report_handles_missing_baseline_and_optional_artifacts(tmp_path):
    output_path = tmp_path / "index.html"

    write_html_report(
        output_path=output_path,
        repo="owner/repo",
        days=7,
        pr_summary=PullRequestMetricsSummary(
            total_prs=0,
            merged_prs=0,
            open_prs=0,
            avg_merge_hours=None,
            median_merge_hours=None,
            avg_pr_size=None,
            avg_changed_files=None,
            avg_comments=None,
            top_authors=[],
        ),
        workflow_summary=WorkflowMetricsSummary(
            total_runs=0,
            successful_runs=0,
            failed_runs=0,
            cancelled_runs=0,
            excluded_runs=0,
            success_rate=None,
            avg_duration_minutes=None,
            failure_categories=[],
            top_failed_workflows=[],
        ),
        digest=WeeklyCiDigest(
            worst_day=None,
            noisiest_category=None,
            most_unstable_workflow=None,
            top_failure_details=[],
            key_risks=[],
            recommended_actions=[],
            repeated_issue_commentary=[],
        ),
        comparison=TrendComparison(baseline_available=False, issues=[]),
        artifact_links={},
    )

    html = output_path.read_text(encoding="utf-8")
    assert "Baseline unavailable" in html
    assert "No recurring CI issues" in html
    assert "No artifact links were generated" in html
