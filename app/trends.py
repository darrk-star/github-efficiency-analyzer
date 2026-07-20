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


def _count_flaky_recurrences(
    observations: list[FailureObservation], fingerprint: str
) -> int:
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
