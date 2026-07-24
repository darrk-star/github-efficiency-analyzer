from datetime import date

from app.metrics import PullRequestMetricsSummary, WeeklyCiDigest, WorkflowMetricsSummary
from app.report import render_weekly_digest, write_markdown_report
from app.trends import RollingTrendComparison, RollingTrendIssue, TrendComparison, TrendIssue


def sample_digest() -> WeeklyCiDigest:
    return WeeklyCiDigest(
        worst_day=None,
        noisiest_category=None,
        most_unstable_workflow=None,
        top_failure_details=[],
        key_risks=[],
        recommended_actions=[],
        repeated_issue_commentary=[],
    )


def test_weekly_digest_marks_missing_baseline():
    output = render_weekly_digest(
        repo="owner/repo",
        days=14,
        digest=sample_digest(),
        comparison=TrendComparison(baseline_available=False, issues=[]),
    )

    assert "## Recurring CI Issues" in output
    assert "Baseline unavailable" in output


def test_weekly_digest_renders_top_actionable_issue():
    comparison = TrendComparison(
        baseline_available=True,
        issues=[
            TrendIssue(
                fingerprint="fp",
                category="test_failure",
                status="regressed",
                current_count=4,
                previous_count=2,
                workflows=["CI"],
                example_detail="pytest failed",
                suspected_flaky=True,
                transition_count=1,
            )
        ],
    )

    output = render_weekly_digest("owner/repo", 14, sample_digest(), comparison)

    assert "`regressed` suspected_flaky" in output
    assert "test_failure (4 occurrences) - pytest failed" in output


def test_weekly_digest_renders_rolling_trends_and_history_collection():
    rolling = RollingTrendComparison(
        observed_windows=4,
        issues=[
            RollingTrendIssue(
                fingerprint="fp",
                category="test_failure",
                window_counts=[1, 2, 4, 7],
                workflows=["CI"],
                example_detail="pytest failed",
                observed_windows=4,
                trend_direction="worsening",
                confidence="high",
                suspected_flaky=True,
                transition_count=1,
            )
        ],
    )

    output = render_weekly_digest(
        "owner/repo",
        14,
        sample_digest(),
        TrendComparison(baseline_available=True, issues=[]),
        rolling,
    )

    assert "## Rolling CI Trends" in output
    assert "1 -> 2 -> 4 -> 7" in output
    assert "data coverage confidence: high" in output
    assert "suspected_flaky" in output


def test_markdown_report_includes_analysis_end_date(tmp_path):
    output_path = tmp_path / "summary.md"

    write_markdown_report(
        output_path,
        "owner/repo",
        14,
        date(2026, 7, 20),
        PullRequestMetricsSummary(0, 0, 0, None, None, None, None, None, []),
        WorkflowMetricsSummary(0, 0, 0, 0, 0, None, None, [], []),
    )

    assert "Analysis end date: 2026-07-20 UTC" in output_path.read_text(encoding="utf-8")


def test_markdown_report_includes_first_review_metrics(tmp_path):
    output_path = tmp_path / "summary.md"
    pr_summary = PullRequestMetricsSummary(
        2, 1, 1, 2.0, 2.0, 10.0, 1.0, 0.0, [("alice", 2)], 3.0, 3.0, 1, [("bob", 1)]
    )

    write_markdown_report(
        output_path,
        "owner/repo",
        14,
        date(2026, 7, 20),
        pr_summary,
        WorkflowMetricsSummary(0, 0, 0, 0, 0, None, None, [], []),
    )

    rendered = output_path.read_text(encoding="utf-8")
    assert "Average first review response (hours): 3.00" in rendered
    assert "PRs without external review: 1" in rendered
    assert "## Top First Reviewers" in rendered
    assert "- bob: 1 first reviews" in rendered
