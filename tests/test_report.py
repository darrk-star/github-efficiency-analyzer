from app.metrics import WeeklyCiDigest
from app.report import render_weekly_digest
from app.trends import TrendComparison, TrendIssue


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
