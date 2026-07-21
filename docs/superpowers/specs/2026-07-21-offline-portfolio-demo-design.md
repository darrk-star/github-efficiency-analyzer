# Offline Portfolio Demo Design

## Goal

Add a deterministic offline demo path so a recruiter or interviewer can run the project without a GitHub token and still see the core portfolio value: PR metrics, CI summaries, recurring failure fingerprints, adjacent snapshot comparison, and Markdown/CSV/JSON outputs.

## Problem

The current CLI demonstrates real GitHub API integration, but a first-time reviewer may not have a token, network access, or time to choose a suitable repository. The v2 snapshot feature is technically useful, but it is hard to demonstrate quickly because it depends on having adjacent-window data. For job-search use, the project needs a zero-credential demo that exercises the same pure metric/report/snapshot code paths.

There is also a README formatting issue in the existing Failure Trend Demo block: it contains literal `` `r`n`` text instead of real line breaks. The offline demo update should fix this while updating the documentation.

## Scope

In scope:

- Add a small committed fixture under `examples/fixtures/`.
- Add an offline demo module that turns fixture data into existing `PullRequestRecord` and `WorkflowRunRecord` objects.
- Reuse existing metric, report, snapshot, trend, and CSV writers rather than duplicating analysis logic.
- Generate a previous snapshot and a current snapshot from fixture data so recurring statuses are visible immediately.
- Add a CLI flag that runs the demo without network calls.
- Add tests proving the offline demo writes expected files and recurring issue output.
- Update README with a no-token portfolio demo command and fix the malformed Failure Trend Demo block.

Out of scope:

- Web UI, dashboard, Streamlit, Flask, FastAPI, or static site generation.
- SQLite or any database.
- LLM/embedding classification.
- Multi-repository analysis.
- Slack, Feishu, email, or other notification integrations.
- Any live GitHub calls in offline demo mode.

## User Experience

The reviewer can run:

```powershell
python -m app.main --demo --output-dir outputs/demo --snapshot-dir outputs/demo/snapshots
```

The command prints a concise summary and writes:

- `outputs/demo/pull_requests.csv`
- `outputs/demo/workflow_runs.csv`
- `outputs/demo/summary.md`
- `outputs/demo/weekly_digest.md`
- `outputs/demo/snapshots/acme__checkout-service__14__2026-07-06.json`
- `outputs/demo/snapshots/acme__checkout-service__14__2026-07-20.json`

The weekly digest includes a `## Recurring CI Issues` section with at least:

- one `regressed` issue
- one `persistent` issue
- one `new` issue
- one `suspected_flaky` signal

The command must not require `GITHUB_TOKEN` and must not instantiate `GitHubClient` for network collection.

## Fixture Design

Create `examples/fixtures/portfolio_demo.json` with plain JSON:

```json
{
  "repo": "acme/checkout-service",
  "days": 14,
  "previous_generated_at": "2026-07-06T12:00:00+00:00",
  "current_generated_at": "2026-07-20T12:00:00+00:00",
  "pull_requests": [
    {
      "number": 101,
      "title": "Reduce checkout retry latency",
      "author": "alice",
      "state": "closed",
      "created_at": "2026-07-10T09:00:00+00:00",
      "updated_at": "2026-07-10T16:30:00+00:00",
      "closed_at": "2026-07-10T16:30:00+00:00",
      "merged_at": "2026-07-10T16:30:00+00:00",
      "additions": 220,
      "deletions": 80,
      "changed_files": 8,
      "review_comments": 5,
      "comments": 3,
      "commits": 4,
      "reviewers": ["bob"],
      "url": "https://example.com/acme/checkout-service/pull/101"
    }
  ],
  "previous_workflow_runs": [
    {
      "id": 9001,
      "name": "CI",
      "event": "pull_request",
      "status": "completed",
      "conclusion": "failure",
      "created_at": "2026-07-05T10:00:00+00:00",
      "updated_at": "2026-07-05T10:20:00+00:00",
      "run_started_at": "2026-07-05T10:00:00+00:00",
      "actor": "alice",
      "branch": "feature/checkout-retry",
      "duration_minutes": 20.0,
      "html_url": "https://example.com/runs/9001",
      "jobs_url": "https://example.com/runs/9001/jobs",
      "failure_category": "test_failure",
      "failure_detail": "pytest failed in tests/test_checkout.py:41"
    }
  ],
  "current_workflow_runs": [
    {
      "id": 9101,
      "name": "CI",
      "event": "pull_request",
      "status": "completed",
      "conclusion": "failure",
      "created_at": "2026-07-19T10:00:00+00:00",
      "updated_at": "2026-07-19T10:18:00+00:00",
      "run_started_at": "2026-07-19T10:00:00+00:00",
      "actor": "alice",
      "branch": "feature/checkout-retry",
      "duration_minutes": 18.0,
      "html_url": "https://example.com/runs/9101",
      "jobs_url": "https://example.com/runs/9101/jobs",
      "failure_category": "test_failure",
      "failure_detail": "pytest failed in tests/test_checkout.py:88"
    }
  ]
}
```

The final fixture should include enough records to create meaningful metrics, but it should stay small and readable. It should not contain secrets or real customer data.

## Implementation Design

Add `app/demo.py` as the only new application module. It owns fixture loading and offline orchestration.

Public API:

```python
from pathlib import Path


def run_demo(output_dir: Path, snapshot_dir: Path) -> tuple[str, list[Path]]:
    ...
```

`run_demo` returns the demo repo name and written paths for CLI printing.

Internal helpers:

- `_load_fixture(path: Path) -> dict[str, object]`
- `_parse_pull_request(item: dict[str, object]) -> PullRequestRecord`
- `_parse_workflow_run(item: dict[str, object]) -> WorkflowRunRecord`
- `_build_snapshot(repo, days, generated_at, records) -> Snapshot`

The demo flow:

1. Load fixture JSON.
2. Convert previous and current workflow arrays into typed records.
3. Build and write the previous snapshot first.
4. Build the current snapshot and compare it to the previous snapshot.
5. Generate current-window PR summary, workflow summary, CSVs, Markdown report, weekly digest, and optional charts using existing functions.
6. Write current snapshot.
7. Return written paths.

The demo may call chart writers. If chart dependencies are present, PNGs are generated; if the data is insufficient, the existing chart behavior remains unchanged.

## CLI Design

Add to `app/main.py`:

```python
parser.add_argument(
    "--demo",
    action="store_true",
    help="Run the offline portfolio demo fixture instead of calling GitHub.",
)
```

Behavior:

- If `--demo` is set, `--repo`, GitHub token, and network collection are not required.
- `--output-dir` and `--snapshot-dir` still control output locations.
- `--days` and `--limit` are ignored in demo mode because fixture metadata defines the analysis window.
- Print a clear line such as `Offline demo: acme/checkout-service`.

## Testing Design

Add `tests/test_demo.py`:

- Fixture parsing returns typed PR and workflow records.
- `run_demo(tmp_path / "outputs", tmp_path / "snapshots")` writes expected files.
- `weekly_digest.md` contains `## Recurring CI Issues`, `regressed`, and `suspected_flaky`.
- Two snapshot JSON files are written with the expected deterministic names.

Modify `tests/test_main.py`:

- `parse_args(["--demo"])` succeeds without `--repo`.
- `run(["--demo", "--output-dir", ..., "--snapshot-dir", ...])` succeeds and does not instantiate `GitHubClient`.

Tests must follow TDD: write failing tests, run them red, implement minimal code, run them green.

## Documentation Design

README changes:

- Add `Offline Portfolio Demo` section near Quick Start.
- Show:

```powershell
python -m app.main --demo --output-dir outputs/demo --snapshot-dir outputs/demo/snapshots
Get-Content outputs/demo/weekly_digest.md
Get-Content outputs/demo/snapshots/*.json
```

- Explain that this path uses committed fixture data and never calls GitHub.
- Fix the malformed Failure Trend Demo block so it uses real line breaks instead of literal `` `r`n``.
- Update test count after implementation.

## Success Criteria

- `python -m app.main --demo --output-dir outputs/demo --snapshot-dir outputs/demo/snapshots` runs without `GITHUB_TOKEN`.
- Demo writes CSV, Markdown, and two snapshot JSON files.
- Weekly digest shows recurring CI issue statuses and suspected flaky signal.
- Existing live GitHub mode remains compatible.
- Full tests pass.
- README accurately explains offline and live demo paths.
