from __future__ import annotations

import argparse
from datetime import datetime, timezone

import pytest

from app.github_client import GitHubApiError
from app.main import format_optional_number, parse_args, positive_int, repo_name, run
from app.models import WorkflowRunRecord
from app.snapshots import (
    FailureIssue,
    Snapshot,
    previous_snapshot_path,
    read_snapshot,
    write_snapshot,
)


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_positive_int_rejects_invalid_values(value):
    with pytest.raises(argparse.ArgumentTypeError, match="positive integer"):
        positive_int(value)


def test_positive_int_accepts_positive_values():
    assert positive_int("7") == 7


@pytest.mark.parametrize("value", ["owner", "/repo", "owner/", "owner/repo/extra"])
def test_repo_name_rejects_invalid_values(value):
    with pytest.raises(argparse.ArgumentTypeError, match="owner/name"):
        repo_name(value)


def test_format_optional_number_preserves_zero():
    assert format_optional_number(0.0) == "0.0"
    assert format_optional_number(None) == "N/A"


def test_parse_args_accepts_snapshot_dir():
    args = parse_args(
        ["--repo", "owner/repo", "--snapshot-dir", "tmp/snapshots"]
    )

    assert args.snapshot_dir == "tmp/snapshots"


def test_parse_args_accepts_demo_mode():
    args = parse_args(["--repo", "owner/repo", "--demo"])

    assert args.demo is True


def test_run_returns_nonzero_for_github_error(monkeypatch, capsys):
    def raise_api_error(*args, **kwargs):
        raise GitHubApiError("GitHub API unavailable")

    monkeypatch.setattr("app.main.GitHubClient.fetch_pull_requests", raise_api_error)

    assert run(["--repo", "owner/repo"]) == 1
    assert "GitHub API unavailable" in capsys.readouterr().err


def test_run_writes_snapshot_and_weekly_digest_with_missing_baseline(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setattr("app.main.GitHubClient.fetch_pull_requests", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        "app.main.GitHubClient.fetch_workflow_runs",
        lambda *args, **kwargs: [_workflow_run()],
    )
    monkeypatch.setattr("app.main.write_failure_trend_chart", lambda *args, **kwargs: False)
    monkeypatch.setattr("app.main.write_failed_workflow_chart", lambda *args, **kwargs: False)

    result = run(
        [
            "--repo",
            "owner/repo",
            "--days",
            "14",
            "--limit",
            "1",
            "--output-dir",
            str(tmp_path / "outputs"),
            "--snapshot-dir",
            str(tmp_path / "snapshots"),
        ]
    )

    assert result == 0
    snapshots = list((tmp_path / "snapshots").glob("owner__repo__14__*.json"))
    assert len(snapshots) == 1
    assert read_snapshot(snapshots[0]).issues[0].example_detail == "pytest failed"
    weekly_digest = (tmp_path / "outputs" / "weekly_digest.md").read_text(
        encoding="utf-8"
    )
    assert "Baseline unavailable" in weekly_digest
    assert "Snapshot: " in capsys.readouterr().out


def test_run_compares_against_adjacent_previous_snapshot(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.GitHubClient.fetch_pull_requests", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        "app.main.GitHubClient.fetch_workflow_runs",
        lambda *args, **kwargs: [_workflow_run()],
    )
    monkeypatch.setattr("app.main.write_failure_trend_chart", lambda *args, **kwargs: False)
    monkeypatch.setattr("app.main.write_failed_workflow_chart", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        "app.main.datetime",
        _FrozenDateTime,
    )
    snapshot_dir = tmp_path / "snapshots"
    previous = _previous_snapshot()
    previous_path = previous_snapshot_path(
        snapshot_dir,
        repo="owner/repo",
        window_days=14,
        current_end_date="2026-07-20",
    )
    write_snapshot(snapshot_dir, previous)
    assert previous_path.exists()

    result = run(
        [
            "--repo",
            "owner/repo",
            "--days",
            "14",
            "--limit",
            "1",
            "--output-dir",
            str(tmp_path / "outputs"),
            "--snapshot-dir",
            str(snapshot_dir),
        ]
    )

    assert result == 0
    weekly_digest = (tmp_path / "outputs" / "weekly_digest.md").read_text(
        encoding="utf-8"
    )
    assert "`persistent`: test_failure (1 occurrences) - pytest failed" in weekly_digest
    assert "Baseline unavailable" not in weekly_digest


def test_run_demo_mode_does_not_use_github_client(monkeypatch, tmp_path):
    called = {"fetch_pull_requests": False, "fetch_workflow_runs": False}

    def fail_pull_requests(*args, **kwargs):
        called["fetch_pull_requests"] = True
        raise AssertionError("live GitHub path should not run in demo mode")

    def fail_workflow_runs(*args, **kwargs):
        called["fetch_workflow_runs"] = True
        raise AssertionError("live GitHub path should not run in demo mode")

    monkeypatch.setattr("app.main.GitHubClient.fetch_pull_requests", fail_pull_requests)
    monkeypatch.setattr("app.main.GitHubClient.fetch_workflow_runs", fail_workflow_runs)

    assert (
        run(
            [
                "--repo",
                "owner/repo",
                "--demo",
                "--output-dir",
                str(tmp_path / "outputs"),
                "--snapshot-dir",
                str(tmp_path / "snapshots"),
            ]
        )
        == 0
    )
    assert called == {
        "fetch_pull_requests": False,
        "fetch_workflow_runs": False,
    }


class _FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)


def _workflow_run() -> WorkflowRunRecord:
    observed_at = datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc)
    return WorkflowRunRecord(
        id=1,
        name="CI",
        event="pull_request",
        status="completed",
        conclusion="failure",
        created_at=observed_at,
        updated_at=observed_at,
        run_started_at=observed_at,
        actor="alice",
        branch="main",
        duration_minutes=10.0,
        html_url="https://example.com/runs/1",
        jobs_url="https://example.com/runs/1/jobs",
        failure_category="test_failure",
        failure_detail="pytest failed",
    )


def _previous_snapshot() -> Snapshot:
    previous_at = datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc)
    fingerprint = "ci-failure-f6510dd02369"
    return Snapshot(
        schema_version=1,
        repo="owner/repo",
        window_days=14,
        generated_at=previous_at,
        total_runs=1,
        failed_runs=1,
        issues=[
            FailureIssue(
                fingerprint=fingerprint,
                category="test_failure",
                normalized_detail="pytest failed",
                example_detail="pytest failed",
                count=1,
                workflows=["CI"],
                first_seen=previous_at,
                last_seen=previous_at,
            )
        ],
        observations=[],
    )
