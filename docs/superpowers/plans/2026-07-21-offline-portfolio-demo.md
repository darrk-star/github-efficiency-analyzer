# Offline Portfolio Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic offline demo mode that exercises the existing PR metrics, CI summaries, snapshot comparison, and report generation without requiring a GitHub token.

**Architecture:** Add one focused demo module that loads a committed fixture, converts it into the existing domain records, and reuses the current metrics/report/snapshot writers. Extend the CLI with a `--demo` mode that bypasses GitHub network collection. Keep the offline path small, deterministic, and easy to explain in a portfolio review.

**Tech Stack:** Python 3.11, dataclasses, pathlib, json, pytest, existing metrics/report/snapshot modules

---

### Task 1: Fix README demo wording before changing behavior

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write the failing documentation expectation**

Add a README check in your head before editing: the Failure Trend Demo block should use real newlines and the repo should advertise an offline demo path rather than only the live GitHub path.

- [ ] **Step 2: Update the README text**

Replace the malformed literal `` `r`n`` block with real line breaks and add a short `Offline Portfolio Demo` section that shows:

```powershell
python -m app.main --demo --output-dir outputs/demo --snapshot-dir outputs/demo/snapshots
Get-Content outputs/demo/weekly_digest.md
Get-Content outputs/demo/snapshots/*.json
```

State that demo mode uses committed fixture data and does not require `GITHUB_TOKEN`.

- [ ] **Step 3: Verify the README reads cleanly**

Run: `Get-Content README.md -Raw`

Expected: the demo section is readable, the Failure Trend Demo block has real newlines, and no literal `` `r`n`` text remains.

- [ ] **Step 4: Commit the documentation cleanup**

```powershell
git add README.md
git commit -m "docs: clarify offline portfolio demo path"
```

### Task 2: Add offline demo fixture and parser helpers

**Files:**
- Create: `examples/fixtures/portfolio_demo.json`
- Create: `app/demo.py`
- Create: `tests/test_demo.py`

- [ ] **Step 1: Write failing fixture parsing tests**

Add tests that load the fixture JSON and assert the parsed objects are real `PullRequestRecord` and `WorkflowRunRecord` instances with the expected repo, generated dates, and workflow counts.

```python
from app.demo import load_demo_fixture


def test_demo_fixture_parses_into_records():
    fixture = load_demo_fixture(Path("examples/fixtures/portfolio_demo.json"))
    assert fixture.repo == "acme/checkout-service"
    assert len(fixture.pull_requests) > 0
    assert len(fixture.previous_workflow_runs) > 0
    assert len(fixture.current_workflow_runs) > 0
```

- [ ] **Step 2: Run the fixture tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_demo.py -v`

Expected: collection error because `app.demo` and the fixture do not exist yet.

- [ ] **Step 3: Implement the demo fixture and loader**

Create `examples/fixtures/portfolio_demo.json` with the committed offline data described in the spec. In `app/demo.py`, define:

```python
from dataclasses import dataclass
from pathlib import Path
from app.models import PullRequestRecord, WorkflowRunRecord


@dataclass(frozen=True)
class DemoFixture:
    repo: str
    days: int
    previous_generated_at: str
    current_generated_at: str
    pull_requests: list[PullRequestRecord]
    previous_workflow_runs: list[WorkflowRunRecord]
    current_workflow_runs: list[WorkflowRunRecord]


def load_demo_fixture(path: Path) -> DemoFixture:
    ...
```

Parse ISO timestamps into `datetime` objects and keep the fixture deterministic and small.

- [ ] **Step 4: Run the fixture tests to verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_demo.py -v`

Expected: fixture parsing tests PASS.

- [ ] **Step 5: Commit the fixture and loader**

```powershell
git add app/demo.py examples/fixtures/portfolio_demo.json tests/test_demo.py
git commit -m "feat: add offline portfolio demo fixture"
```

### Task 3: Build the offline demo orchestration

**Files:**
- Modify: `app/demo.py`
- Modify: `app/metrics.py` if needed for fixture reuse only
- Modify: `tests/test_demo.py`

- [ ] **Step 1: Write a failing end-to-end demo test**

Add a test that runs the demo into a temp directory and checks for:

```python
output_dir = tmp_path / "outputs"
snapshot_dir = tmp_path / "snapshots"
repo, paths = run_demo(output_dir, snapshot_dir)
assert repo == "acme/checkout-service"
assert (output_dir / "weekly_digest.md").exists()
assert (snapshot_dir / "acme__checkout-service__14__2026-07-06.json").exists()
assert (snapshot_dir / "acme__checkout-service__14__2026-07-20.json").exists()
```

- [ ] **Step 2: Run the demo test to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_demo.py -k run_demo -v`

Expected: failure because `run_demo` does not exist yet.

- [ ] **Step 3: Implement the demo pipeline**

Add `run_demo(output_dir: Path, snapshot_dir: Path) -> tuple[str, list[Path]]` in `app/demo.py`. Reuse existing metrics/report/snapshot helpers so the demo exercises the real production code path:

```python
from app.metrics import build_failure_issues, build_pr_rows, build_workflow_rows, summarize_pull_requests, summarize_workflow_runs, build_weekly_ci_digest, build_daily_failure_trend, build_failed_workflow_breakdown, write_rows_to_csv
from app.report import write_markdown_report, write_weekly_digest_report
from app.snapshots import Snapshot, write_snapshot
from app.trends import compare_snapshots
```

Write the previous snapshot first, then the current snapshot, and render the weekly digest with the comparison so the output contains recurring issue statuses.

- [ ] **Step 4: Run the demo tests to verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_demo.py -v`

Expected: demo end-to-end tests PASS.

- [ ] **Step 5: Commit the offline demo pipeline**

```powershell
git add app/demo.py tests/test_demo.py
git commit -m "feat: add offline portfolio demo orchestration"
```

### Task 4: Wire `--demo` into the CLI

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_main.py`

- [ ] **Step 1: Write failing CLI tests**

Add tests that prove:

```python
args = parse_args(["--demo"])
assert args.demo is True

result = run(["--demo", "--output-dir", str(tmp_path / "outputs"), "--snapshot-dir", str(tmp_path / "snapshots")])
assert result == 0
```

Also assert that the demo path does not instantiate `GitHubClient`.

- [ ] **Step 2: Run the CLI tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_main.py -k demo -v`

Expected: failure because `--demo` is unsupported.

- [ ] **Step 3: Implement CLI branching for demo mode**

Add `--demo` to `parse_args`. In `run`, branch early:

```python
if args.demo:
    from app.demo import run_demo
    run_demo(Path(args.output_dir), Path(args.snapshot_dir))
    return 0
```

Ensure live GitHub mode remains unchanged when `--demo` is absent.

- [ ] **Step 4: Run the CLI tests to verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_main.py -k demo -v`

Expected: CLI demo tests PASS.

- [ ] **Step 5: Commit the CLI integration**

```powershell
git add app/main.py tests/test_main.py
git commit -m "feat: wire offline demo mode into the CLI"
```

### Task 5: Final documentation and verification

**Files:**
- Modify: `README.md`
- Possibly modify: `app/demo.py`, `tests/test_demo.py`, `tests/test_main.py`

- [ ] **Step 1: Update README demo instructions**

Make sure the README includes both:

1. the offline demo command
2. the live GitHub mode command

Keep the offline path clearly labeled as portfolio-friendly and no-token.

- [ ] **Step 2: Run the targeted verification**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_demo.py tests/test_main.py -v
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q app tests
git diff --check
```

Expected: all checks pass cleanly.

- [ ] **Step 3: Commit the documentation finalization**

```powershell
git add README.md
git commit -m "docs: document offline portfolio demo"
```

### Task 6: Final review

**Files:**
- None unless verification reveals a mismatch

- [ ] **Step 1: Inspect repository status**

Run: `git status --short --branch`

Expected: only the intentional demo commits are present and the worktree is clean after the final commit.

- [ ] **Step 2: Review the README claims against the implementation**

Check that the README matches the actual demo command, file names, and test counts. Correct any mismatch before handing off.

- [ ] **Step 3: Present completion options**

After verification, use the finishing-a-development-branch workflow and present the standard integration options to the user.
