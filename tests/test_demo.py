from pathlib import Path

from app.demo import load_demo_fixture, run_demo
from app.models import PullRequestRecord, WorkflowRunRecord


def test_demo_fixture_parses_into_records():
    fixture = load_demo_fixture(Path("examples/fixtures/portfolio_demo.json"))

    assert fixture.repo == "acme/checkout-service"
    assert fixture.days == 14
    assert fixture.pull_requests
    assert fixture.previous_workflow_runs
    assert fixture.current_workflow_runs
    assert isinstance(fixture.pull_requests[0], PullRequestRecord)
    assert isinstance(fixture.current_workflow_runs[0], WorkflowRunRecord)


def test_run_demo_writes_reports_and_adjacent_snapshots(tmp_path):
    output_dir = tmp_path / "outputs"
    snapshot_dir = tmp_path / "snapshots"

    repo, paths = run_demo(output_dir, snapshot_dir)

    assert repo == "acme/checkout-service"
    assert output_dir / "pull_requests.csv" in paths
    assert output_dir / "workflow_runs.csv" in paths
    assert output_dir / "summary.md" in paths
    assert output_dir / "weekly_digest.md" in paths
    assert (
        snapshot_dir / "acme__checkout-service__14__2026-07-06.json"
        in paths
    )
    assert (
        snapshot_dir / "acme__checkout-service__14__2026-07-20.json"
        in paths
    )

    weekly_digest = (output_dir / "weekly_digest.md").read_text(encoding="utf-8")
    assert "## Recurring CI Issues" in weekly_digest
    assert "`regressed`" in weekly_digest
    assert "`persistent`" in weekly_digest
    assert "`new`" in weekly_digest
    assert "suspected_flaky" in weekly_digest


def test_run_demo_keeps_core_outputs_when_chart_backend_fails(monkeypatch, tmp_path):
    def raise_chart_error(*args, **kwargs):
        raise RuntimeError("chart backend unavailable")

    monkeypatch.setattr("app.demo.write_failure_trend_chart", raise_chart_error)
    monkeypatch.setattr("app.demo.write_failed_workflow_chart", raise_chart_error)

    repo, paths = run_demo(tmp_path / "outputs", tmp_path / "snapshots")

    assert repo == "acme/checkout-service"
    assert tmp_path / "outputs" / "weekly_digest.md" in paths
    assert (
        tmp_path / "snapshots" / "acme__checkout-service__14__2026-07-20.json"
        in paths
    )
