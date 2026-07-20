from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


ObservationOutcome = Literal["success", "failed"]


@dataclass(frozen=True)
class FailureIssue:
    fingerprint: str
    category: str
    normalized_detail: str
    example_detail: str
    count: int
    workflows: list[str]
    first_seen: datetime
    last_seen: datetime


@dataclass(frozen=True)
class FailureObservation:
    observed_at: datetime
    workflow: str
    outcome: ObservationOutcome
    fingerprint: str | None


@dataclass(frozen=True)
class Snapshot:
    schema_version: int
    repo: str
    window_days: int
    generated_at: datetime
    total_runs: int
    failed_runs: int
    issues: list[FailureIssue]
    observations: list[FailureObservation]


def snapshot_filename(repo: str, window_days: int, end_date: str) -> str:
    safe_repo = repo.replace("/", "__")
    return f"{safe_repo}__{window_days}__{end_date}.json"


def write_snapshot(directory: Path, snapshot: Snapshot) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / snapshot_filename(
        snapshot.repo,
        snapshot.window_days,
        snapshot.generated_at.date().isoformat(),
    )
    payload = _snapshot_to_dict(snapshot)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def read_snapshot(path: Path) -> Snapshot:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError(f"Unsupported snapshot schema version: {payload.get('schema_version')}")

    issues = [
        FailureIssue(
            fingerprint=item["fingerprint"],
            category=item["category"],
            normalized_detail=item["normalized_detail"],
            example_detail=item["example_detail"],
            count=item["count"],
            workflows=list(item["workflows"]),
            first_seen=datetime.fromisoformat(item["first_seen"]),
            last_seen=datetime.fromisoformat(item["last_seen"]),
        )
        for item in payload["issues"]
    ]
    observations = [
        FailureObservation(
            observed_at=datetime.fromisoformat(item["observed_at"]),
            workflow=item["workflow"],
            outcome=item["outcome"],
            fingerprint=item.get("fingerprint"),
        )
        for item in payload["observations"]
    ]
    return Snapshot(
        schema_version=payload["schema_version"],
        repo=payload["repo"],
        window_days=payload["window_days"],
        generated_at=datetime.fromisoformat(payload["generated_at"]),
        total_runs=payload["total_runs"],
        failed_runs=payload["failed_runs"],
        issues=issues,
        observations=observations,
    )


def _snapshot_to_dict(snapshot: Snapshot) -> dict[str, object]:
    issues = []
    for issue in sorted(snapshot.issues, key=lambda item: (-item.count, item.fingerprint)):
        payload = asdict(issue)
        payload["workflows"] = sorted(issue.workflows)
        payload["first_seen"] = issue.first_seen.isoformat()
        payload["last_seen"] = issue.last_seen.isoformat()
        issues.append(payload)

    observations = []
    for observation in sorted(snapshot.observations, key=lambda item: item.observed_at):
        payload = asdict(observation)
        payload["observed_at"] = observation.observed_at.isoformat()
        observations.append(payload)

    return {
        "schema_version": snapshot.schema_version,
        "repo": snapshot.repo,
        "window_days": snapshot.window_days,
        "generated_at": snapshot.generated_at.isoformat(),
        "total_runs": snapshot.total_runs,
        "failed_runs": snapshot.failed_runs,
        "issues": issues,
        "observations": observations,
    }
