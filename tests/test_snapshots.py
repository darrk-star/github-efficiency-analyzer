from dataclasses import replace
from datetime import UTC, datetime, timedelta

from app.snapshots import (
    FailureIssue,
    FailureObservation,
    Snapshot,
    load_recent_snapshots,
    previous_snapshot_path,
    read_snapshot,
    snapshot_filename,
    write_snapshot,
)


def sample_snapshot() -> Snapshot:
    return Snapshot(
        schema_version=1,
        repo="owner/repo",
        window_days=14,
        generated_at=datetime(2026, 7, 20, tzinfo=UTC),
        total_runs=10,
        failed_runs=2,
        issues=[
            FailureIssue(
                fingerprint="ci-failure-a1b2c3d4",
                category="test_failure",
                normalized_detail="pytest failed in test_api.py:{line}",
                example_detail="pytest failed in test_api.py:42",
                count=2,
                workflows=["CI"],
                first_seen=datetime(2026, 7, 19, tzinfo=UTC),
                last_seen=datetime(2026, 7, 20, tzinfo=UTC),
            )
        ],
        observations=[
            FailureObservation(
                observed_at=datetime(2026, 7, 20, tzinfo=UTC),
                workflow="CI",
                outcome="failed",
                fingerprint="ci-failure-a1b2c3d4",
            )
        ],
    )


def test_snapshot_round_trip_uses_stable_json_without_full_logs(tmp_path):
    original = sample_snapshot()

    path = write_snapshot(tmp_path, original)
    loaded = read_snapshot(path)

    assert loaded == original
    serialized = path.read_text(encoding="utf-8")
    assert '"schema_version": 1' in serialized
    assert "log_text" not in serialized


def test_snapshot_filename_is_deterministic():
    assert snapshot_filename("owner/repo", 14, "2026-07-20") == "owner__repo__14__2026-07-20.json"


def test_previous_snapshot_path_uses_adjacent_equal_window(tmp_path):
    path = previous_snapshot_path(
        tmp_path,
        repo="owner/repo",
        window_days=14,
        current_end_date="2026-07-20",
    )

    assert path.name == "owner__repo__14__2026-07-06.json"


def test_load_recent_snapshots_returns_adjacent_compatible_chain_oldest_first(tmp_path):
    current = sample_snapshot()
    previous = replace(current, generated_at=current.generated_at - timedelta(days=14))
    older = replace(current, generated_at=current.generated_at - timedelta(days=28))
    write_snapshot(tmp_path, older)
    write_snapshot(tmp_path, previous)

    assert load_recent_snapshots(tmp_path, current, windows=4) == [older, previous, current]


def test_load_recent_snapshots_stops_at_missing_or_invalid_history(tmp_path):
    current = sample_snapshot()
    previous = replace(current, generated_at=current.generated_at - timedelta(days=14))
    write_snapshot(tmp_path, previous)

    assert load_recent_snapshots(tmp_path, current, windows=4) == [previous, current]

    malformed_path = tmp_path / snapshot_filename("owner/repo", 14, "2026-06-22")
    malformed_path.write_text("{bad", encoding="utf-8")
    assert load_recent_snapshots(tmp_path, current, windows=4) == [previous, current]


def test_load_recent_snapshots_stops_when_metadata_does_not_match(tmp_path):
    current = sample_snapshot()
    incompatible = replace(
        current,
        repo="other/repo",
        generated_at=current.generated_at - timedelta(days=14),
    )
    expected_path = tmp_path / snapshot_filename("owner/repo", 14, "2026-07-06")
    write_snapshot(tmp_path, incompatible)
    incompatible_path = tmp_path / snapshot_filename("other/repo", 14, "2026-07-06")
    incompatible_path.replace(expected_path)

    assert load_recent_snapshots(tmp_path, current, windows=4) == [current]
