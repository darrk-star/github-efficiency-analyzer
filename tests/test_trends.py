from datetime import datetime, timedelta, timezone

from app.snapshots import FailureIssue, FailureObservation, Snapshot
from app.trends import compare_snapshots


BASE = datetime(2026, 7, 20, tzinfo=timezone.utc)


def issue(fingerprint: str, count: int) -> FailureIssue:
    return FailureIssue(
        fingerprint=fingerprint,
        category="test_failure",
        normalized_detail=f"detail {fingerprint}",
        example_detail=f"Example {fingerprint}",
        count=count,
        workflows=["CI"],
        first_seen=BASE,
        last_seen=BASE,
    )


def observation(
    minute: int,
    workflow: str,
    outcome: str,
    fingerprint: str | None,
) -> FailureObservation:
    return FailureObservation(
        observed_at=BASE + timedelta(minutes=minute),
        workflow=workflow,
        outcome=outcome,
        fingerprint=fingerprint,
    )


def snapshot(
    issues: list[FailureIssue],
    observations: list[FailureObservation] | None = None,
) -> Snapshot:
    return Snapshot(
        schema_version=1,
        repo="owner/repo",
        window_days=14,
        generated_at=BASE,
        total_runs=10,
        failed_runs=sum(item.count for item in issues),
        issues=issues,
        observations=observations or [],
    )


def test_compare_snapshots_assigns_issue_lifecycle_statuses():
    previous = snapshot([issue("persistent", 2), issue("regressed", 1), issue("resolved", 3)])
    current = snapshot([issue("persistent", 2), issue("regressed", 4), issue("new", 1)])

    result = compare_snapshots(previous, current)

    assert result.baseline_available is True
    assert {item.fingerprint: item.status for item in result.issues} == {
        "persistent": "persistent",
        "regressed": "regressed",
        "new": "new",
        "resolved": "resolved",
    }


def test_missing_baseline_marks_current_issues_new():
    result = compare_snapshots(None, snapshot([issue("new", 2)]))

    assert result.baseline_available is False
    assert result.issues[0].status == "new"


def test_fail_success_fail_on_same_workflow_is_suspected_flaky():
    previous = snapshot(
        [issue("fp", 1)],
        [observation(0, "CI", "failed", "fp"), observation(1, "CI", "success", None)],
    )
    current = snapshot([issue("fp", 1)], [observation(2, "CI", "failed", "fp")])

    trend_issue = compare_snapshots(previous, current).issues[0]

    assert trend_issue.suspected_flaky is True
    assert trend_issue.transition_count == 1


def test_consecutive_failures_are_not_suspected_flaky():
    previous = snapshot([issue("fp", 1)], [observation(0, "CI", "failed", "fp")])
    current = snapshot([issue("fp", 1)], [observation(1, "CI", "failed", "fp")])

    assert compare_snapshots(previous, current).issues[0].suspected_flaky is False


def test_different_fingerprints_around_success_are_not_suspected_flaky():
    previous = snapshot(
        [issue("first", 1)],
        [observation(0, "CI", "failed", "first"), observation(1, "CI", "success", None)],
    )
    current = snapshot([issue("second", 1)], [observation(2, "CI", "failed", "second")])

    by_fingerprint = {item.fingerprint: item for item in compare_snapshots(previous, current).issues}

    assert by_fingerprint["first"].suspected_flaky is False
    assert by_fingerprint["second"].suspected_flaky is False
