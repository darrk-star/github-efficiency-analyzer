from __future__ import annotations

from dataclasses import dataclass

from app.snapshots import FailureIssue, FailureObservation, Snapshot


@dataclass(frozen=True)
class TrendIssue:
    fingerprint: str
    category: str
    status: str
    current_count: int
    previous_count: int
    workflows: list[str]
    example_detail: str
    suspected_flaky: bool
    transition_count: int


@dataclass(frozen=True)
class TrendComparison:
    baseline_available: bool
    issues: list[TrendIssue]


@dataclass(frozen=True)
class RollingTrendIssue:
    fingerprint: str
    category: str
    window_counts: list[int]
    workflows: list[str]
    example_detail: str
    observed_windows: int
    trend_direction: str
    confidence: str
    suspected_flaky: bool
    transition_count: int


@dataclass(frozen=True)
class RollingTrendComparison:
    issues: list[RollingTrendIssue]
    observed_windows: int


def build_rolling_trends(snapshots: list[Snapshot]) -> RollingTrendComparison:
    issue_by_fingerprint = {
        issue.fingerprint: issue for snapshot in snapshots for issue in snapshot.issues
    }
    observations = [observation for snapshot in snapshots for observation in snapshot.observations]
    issues: list[RollingTrendIssue] = []

    for fingerprint, issue in issue_by_fingerprint.items():
        window_counts = [
            next(
                (
                    candidate.count
                    for candidate in snapshot.issues
                    if candidate.fingerprint == fingerprint
                ),
                0,
            )
            for snapshot in snapshots
        ]
        transition_count = _count_flaky_recurrences(observations, fingerprint)
        issues.append(
            RollingTrendIssue(
                fingerprint=fingerprint,
                category=issue.category,
                window_counts=window_counts,
                workflows=sorted(issue.workflows),
                example_detail=issue.example_detail,
                observed_windows=len(snapshots),
                trend_direction=_rolling_direction(window_counts),
                confidence=_rolling_confidence(len(snapshots)),
                suspected_flaky=transition_count > 0,
                transition_count=transition_count,
            )
        )

    priority = {"worsening": 0, "stable": 1, "improving": 2, "insufficient_data": 3}
    issues.sort(
        key=lambda item: (
            priority[item.trend_direction],
            -item.window_counts[-1],
            item.fingerprint,
        )
    )
    return RollingTrendComparison(issues=issues, observed_windows=len(snapshots))


def compare_snapshots(previous: Snapshot | None, current: Snapshot) -> TrendComparison:
    previous_by_fingerprint = {
        issue.fingerprint: issue for issue in (previous.issues if previous else [])
    }
    current_by_fingerprint = {issue.fingerprint: issue for issue in current.issues}
    observations = (previous.observations if previous else []) + current.observations

    trend_issues: list[TrendIssue] = []
    for fingerprint, current_issue in current_by_fingerprint.items():
        previous_issue = previous_by_fingerprint.get(fingerprint)
        if previous_issue is None:
            status = "new"
            previous_count = 0
        elif current_issue.count > previous_issue.count:
            status = "regressed"
            previous_count = previous_issue.count
        else:
            status = "persistent"
            previous_count = previous_issue.count

        transition_count = _count_flaky_recurrences(observations, fingerprint)
        trend_issues.append(
            _build_trend_issue(
                current_issue,
                status=status,
                current_count=current_issue.count,
                previous_count=previous_count,
                transition_count=transition_count,
            )
        )

    for fingerprint, previous_issue in previous_by_fingerprint.items():
        if fingerprint in current_by_fingerprint:
            continue
        transition_count = _count_flaky_recurrences(observations, fingerprint)
        trend_issues.append(
            _build_trend_issue(
                previous_issue,
                status="resolved",
                current_count=0,
                previous_count=previous_issue.count,
                transition_count=transition_count,
            )
        )

    priority = {"regressed": 0, "new": 1, "persistent": 2, "resolved": 3}
    trend_issues.sort(
        key=lambda item: (
            priority[item.status],
            -item.current_count,
            -item.previous_count,
            item.fingerprint,
        )
    )
    return TrendComparison(baseline_available=previous is not None, issues=trend_issues)


def _rolling_direction(window_counts: list[int]) -> str:
    if len(window_counts) < 2:
        return "insufficient_data"
    if window_counts[-1] > window_counts[0]:
        return "worsening"
    if window_counts[-1] < window_counts[0]:
        return "improving"
    return "stable"


def _rolling_confidence(observed_windows: int) -> str:
    if observed_windows == 1:
        return "low"
    if observed_windows < 4:
        return "medium"
    return "high"


def _build_trend_issue(
    issue: FailureIssue,
    *,
    status: str,
    current_count: int,
    previous_count: int,
    transition_count: int,
) -> TrendIssue:
    return TrendIssue(
        fingerprint=issue.fingerprint,
        category=issue.category,
        status=status,
        current_count=current_count,
        previous_count=previous_count,
        workflows=sorted(issue.workflows),
        example_detail=issue.example_detail,
        suspected_flaky=transition_count > 0,
        transition_count=transition_count,
    )


def _count_flaky_recurrences(observations: list[FailureObservation], fingerprint: str) -> int:
    by_workflow: dict[str, list[FailureObservation]] = {}
    for observation in observations:
        by_workflow.setdefault(observation.workflow, []).append(observation)

    transitions = 0
    for workflow_observations in by_workflow.values():
        ordered = sorted(workflow_observations, key=lambda item: item.observed_at)
        for start_index, start in enumerate(ordered):
            if start.outcome != "failed" or start.fingerprint != fingerprint:
                continue
            saw_success = False
            for later in ordered[start_index + 1 :]:
                if later.outcome == "success":
                    saw_success = True
                    continue
                if saw_success and later.fingerprint == fingerprint:
                    transitions += 1
                    break
    return transitions
