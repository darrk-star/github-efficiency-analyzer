from datetime import datetime, timezone

from app.snapshots import (
    FailureIssue,
    FailureObservation,
    Snapshot,
    read_snapshot,
    snapshot_filename,
    write_snapshot,
)


def sample_snapshot() -> Snapshot:
    return Snapshot(
        schema_version=1,
        repo="owner/repo",
        window_days=14,
        generated_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
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
                first_seen=datetime(2026, 7, 19, tzinfo=timezone.utc),
                last_seen=datetime(2026, 7, 20, tzinfo=timezone.utc),
            )
        ],
        observations=[
            FailureObservation(
                observed_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
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
    assert (
        snapshot_filename("owner/repo", 14, "2026-07-20")
        == "owner__repo__14__2026-07-20.json"
    )
