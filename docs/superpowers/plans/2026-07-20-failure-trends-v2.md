# Failure Trends v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic CI failure fingerprints, compact JSON snapshots, temporal issue lifecycle comparison, and suspected-flaky signals to the existing portfolio CLI.

**Architecture:** Keep the v1 CLI and typed records intact. Add pure fingerprint and trend modules, a small JSON snapshot persistence module, and thin integrations in metrics, reporting, and CLI orchestration. Comparisons operate only on snapshots and never perform network calls.

**Tech Stack:** Python 3.11, dataclasses, hashlib, json, pathlib, pytest, existing requests/pandas/matplotlib stack

---

## File Structure

- Create `app/failure_fingerprint.py`: noise normalization and stable SHA-256 fingerprint functions.
- Create `app/snapshots.py`: typed snapshot/issue/observation models, deterministic filenames, JSON read/write.
- Create `app/trends.py`: lifecycle comparison and suspected-flaky detection.
- Modify `app/metrics.py`: aggregate failed workflow records into snapshot issues and compact observations.
- Modify `app/report.py`: render recurring issue and trend sections without redefining statuses.
- Modify `app/main.py`: add `--snapshot-dir`, write current snapshots, load adjacent baseline, and pass trend data to reports.
- Modify `tests/test_metrics.py`: prove existing v1 metrics remain unchanged and add issue aggregation tests.
- Create `tests/test_failure_fingerprint.py`: normalization and fingerprint tests.
- Create `tests/test_snapshots.py`: schema, round-trip, filename, and no-log-persistence tests.
- Create `tests/test_trends.py`: lifecycle, regression, resolved, baseline, and flaky tests.
- Modify `tests/test_main.py`: snapshot CLI argument and baseline-unavailable tests.
- Modify `README.md`: explain v2 recurring-failure workflow and local demo.

### Task 1: Implement Stable Failure Fingerprints

**Files:**
- Create: `app/failure_fingerprint.py`
- Create: `tests/test_failure_fingerprint.py`

- [ ] **Step 1: Write failing normalization tests**

```python
from app.failure_fingerprint import normalize_failure_detail


def test_normalization_replaces_volatile_tokens_but_preserves_error_context():
    first = normalize_failure_detail(
        "2026-07-20T10:11:12Z ERROR C:\\builds\\repo\\tests\\test_api.py:42 request 12345 failed"
    )
    second = normalize_failure_detail(
        "2026-07-21T09:01:03Z ERROR /tmp/work/tests/test_api.py:99 request 67890 failed"
    )

    assert first == second
    assert "error" in first
    assert "failed" in first


def test_missing_detail_uses_stable_unknown_token():
    assert normalize_failure_detail("") == "unknown"
```

- [ ] **Step 2: Run tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_failure_fingerprint.py -v`

Expected: collection ERROR because `app.failure_fingerprint` does not exist.

- [ ] **Step 3: Implement normalization**

Create `app/failure_fingerprint.py`:

```python
from __future__ import annotations

import hashlib
import re


_VOLATILE_PATTERNS = (
    (re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\b"), "{timestamp}"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b", re.IGNORECASE), "{uuid}"),
    (re.compile(r"(?i)(?:[A-Z]:)?[/\\](?:[^\s/:]+[/\\])+"), "{path}/"),
    (re.compile(r"(?<=:)\d+\b"), "{line}"),
    (re.compile(r"\b\d{4,}\b"), "{number}"),
)


def normalize_failure_detail(detail: str | None) -> str:
    normalized = " ".join((detail or "").lower().split())
    if not normalized:
        return "unknown"
    for pattern, replacement in _VOLATILE_PATTERNS:
        normalized = pattern.sub(replacement, normalized)
    return normalized


def build_failure_fingerprint(category: str, detail: str | None) -> str:
    payload = f"{category.lower()}::{normalize_failure_detail(detail)}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"ci-failure-{digest}"
```

- [ ] **Step 4: Add deterministic hash and category-separation tests**

```python
from app.failure_fingerprint import build_failure_fingerprint


def test_fingerprint_is_stable_and_category_aware():
    assert build_failure_fingerprint("test_failure", "pytest failed") == build_failure_fingerprint(
        "test_failure", "pytest failed"
    )
    assert build_failure_fingerprint("test_failure", "pytest failed") != build_failure_fingerprint(
        "build_failure", "pytest failed"
    )
```

- [ ] **Step 5: Run fingerprint tests to verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_failure_fingerprint.py -v`

Expected: all fingerprint tests PASS.

- [ ] **Step 6: Commit fingerprint module**

```powershell
git add app/failure_fingerprint.py tests/test_failure_fingerprint.py
git commit -m "feat: add deterministic CI failure fingerprints"
```

### Task 2: Add Compact JSON Snapshots

**Files:**
- Create: `app/snapshots.py`
- Create: `tests/test_snapshots.py`

- [ ] **Step 1: Write failing snapshot round-trip tests**

```python
from datetime import datetime, timezone

from app.snapshots import FailureIssue, FailureObservation, Snapshot, read_snapshot, write_snapshot


def sample_snapshot():
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
    assert "log_text" not in path.read_text(encoding="utf-8")


def test_snapshot_filename_is_deterministic():
    assert snapshot_filename("owner/repo", 14, "2026-07-20") == "owner__repo__14__2026-07-20.json"
```

- [ ] **Step 2: Run snapshot tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_snapshots.py -v`

Expected: collection ERROR because `app.snapshots` does not exist.

- [ ] **Step 3: Implement snapshot dataclasses and serialization**

Create frozen dataclasses `FailureIssue`, `FailureObservation`, and `Snapshot`. Serialize timestamps with `.isoformat()`, sort issues by `(-count, fingerprint)`, sort workflows, and write UTF-8 JSON with `indent=2` and a trailing newline. `read_snapshot` reconstructs the same dataclasses and validates `schema_version == 1`.

Implement:

```python
def snapshot_filename(repo: str, window_days: int, end_date: str) -> str:
    safe_repo = repo.replace("/", "__")
    return f"{safe_repo}__{window_days}__{end_date}.json"
```

`write_snapshot(directory, snapshot)` creates the directory and returns the exact path. It must never serialize raw logs or tokens.

- [ ] **Step 4: Run snapshot tests to verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_snapshots.py -v`

Expected: all snapshot tests PASS.

- [ ] **Step 5: Commit snapshot persistence**

```powershell
git add app/snapshots.py tests/test_snapshots.py
git commit -m "feat: persist compact CI analysis snapshots"
```

### Task 3: Compare Trend Lifecycles and Detect Suspected Flakiness

**Files:**
- Create: `app/trends.py`
- Create: `tests/test_trends.py`

- [ ] **Step 1: Write lifecycle comparison tests**

Use `FailureIssue` fixtures with fingerprints `persistent`, `regressed`, `new`, and a previous-only `resolved` issue. Assert statuses exactly:

```python
result = compare_snapshots(previous, current)
assert {item.fingerprint: item.status for item in result.issues} == {
    "persistent": "persistent",
    "regressed": "regressed",
    "new": "new",
    "resolved": "resolved",
}
```

- [ ] **Step 2: Run lifecycle tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_trends.py -k lifecycle -v`

Expected: collection ERROR because `app.trends` does not exist.

- [ ] **Step 3: Implement lifecycle comparison**

Create:

```python
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
    previous_by_fingerprint = {issue.fingerprint: issue for issue in (previous.issues if previous else [])}
    current_by_fingerprint = {issue.fingerprint: issue for issue in current.issues}
    # Emit current issues with new/persistent/regressed status, then previous-only resolved issues.
    return TrendComparison(
        baseline_available=previous is not None,
        issues=_build_trend_issues(previous_by_fingerprint, current_by_fingerprint, previous, current),
    )
```

Statuses use `new` when absent before, `persistent` when counts are equal or lower, `regressed` when current count is greater, and `resolved` for previous-only fingerprints. Sort active issues before resolved issues by status priority and count.

- [ ] **Step 4: Write failing flaky tests**

```python
def test_fail_success_fail_on_same_workflow_is_suspected_flaky():
    previous = snapshot_with_observations(
        [("CI", "failed", "fp"), ("CI", "success", None)]
    )
    current = snapshot_with_observations([("CI", "failed", "fp")])

    issue = compare_snapshots(previous, current).issues[0]

    assert issue.suspected_flaky is True
    assert issue.transition_count == 1


def test_consecutive_failures_are_not_suspected_flaky():
    previous = snapshot_with_observations([("CI", "failed", "fp")])
    current = snapshot_with_observations([("CI", "failed", "fp")])

    assert compare_snapshots(previous, current).issues[0].suspected_flaky is False
```

- [ ] **Step 5: Implement flaky detection**

Combine observations sorted by `observed_at`, group by workflow, and count `failed(fp) -> success -> failed(fp)` subsequences. Set `suspected_flaky` when the count is positive. Do not mark failures with different fingerprints around a success.

- [ ] **Step 6: Run trend tests to verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_trends.py -v`

Expected: all lifecycle and flaky tests PASS.

- [ ] **Step 7: Commit trend comparison**

```powershell
git add app/trends.py tests/test_trends.py
git commit -m "feat: compare CI issue trends and flag suspected flaky failures"
```

### Task 4: Aggregate Issues Without Changing v1 Metrics

**Files:**
- Modify: `app/metrics.py`
- Modify: `tests/test_metrics.py`

- [ ] **Step 1: Write failing issue aggregation tests**

Create failed `WorkflowRunRecord` fixtures with equivalent noisy details and assert:

```python
issues, observations = build_failure_issues(records)
assert issues[0].count == 2
assert issues[0].workflows == ["CI"]
assert len(observations) == len(records)
assert observations[0].fingerprint == observations[1].fingerprint
```

Include a successful record and assert its observation has `outcome == "success"` and `fingerprint is None`.

- [ ] **Step 2: Run aggregation tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_metrics.py -k failure_issues -v`

Expected: collection ERROR because `build_failure_issues` does not exist.

- [ ] **Step 3: Implement issue aggregation**

Add:

```python
def build_failure_issues(
    records: list[WorkflowRunRecord],
) -> tuple[list[FailureIssue], list[FailureObservation]]:
    """Build compact issue aggregates and per-run observations from workflow records."""
```

For each completed record, create an observation. Failed records use `build_failure_fingerprint`; successful records use `fingerprint=None`. Aggregate failed records by fingerprint, preserve the first example detail, track sorted workflow names, and calculate first/last seen timestamps. Do not alter `summarize_workflow_runs` or existing output row fields except adding already-modeled `failure_source`.

- [ ] **Step 4: Run metric and full tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_metrics.py -v`

Expected: all metric tests PASS.

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: all v1 and v2 tests PASS.

- [ ] **Step 5: Commit issue aggregation**

```powershell
git add app/metrics.py tests/test_metrics.py
git commit -m "feat: aggregate workflow failures into issue clusters"
```

### Task 5: Integrate Snapshots, Trends, and Report Output

**Files:**
- Modify: `app/main.py`
- Modify: `app/report.py`
- Modify: `tests/test_main.py`
- Modify: `tests/test_snapshots.py`

- [ ] **Step 1: Write failing CLI/parser tests**

```python
def test_parse_args_accepts_snapshot_dir():
    args = parse_args(["--repo", "owner/repo", "--snapshot-dir", "tmp/snapshots"])
    assert args.snapshot_dir == "tmp/snapshots"


def test_report_marks_missing_baseline(tmp_path):
    # Call the report helper with a comparison whose baseline_available is False.
    output = render_weekly_digest(
        repo="owner/repo",
        days=14,
        digest=sample_digest(),
        comparison=TrendComparison(baseline_available=False, issues=[]),
    )
    assert "Baseline unavailable" in output
```

- [ ] **Step 2: Run integration tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_main.py -k snapshot -v`

Expected: FAIL because `--snapshot-dir` and recurring-issue rendering do not exist.

- [ ] **Step 3: Add snapshot CLI option and baseline lookup**

Add to `parse_args`:

```python
parser.add_argument(
    "--snapshot-dir",
    default="outputs/snapshots",
    help="Directory for compact CI trend snapshots.",
)
```

In `run`, after workflow records are collected:

1. Call `build_failure_issues`.
2. Construct a `Snapshot` with repository, window, generated time, total/failed counts, issues, and observations.
3. Write it to `snapshot_dir` using the deterministic filename helper.
4. Resolve the previous equal-window snapshot by subtracting `days` from the current window end date.
5. Call `compare_snapshots(previous, current)` and pass the comparison to the report writer.

When no previous file exists, use `TrendComparison(baseline_available=False, issues=current_issues)` and do not fail the run.

- [ ] **Step 4: Render recurring issues and baseline state**

Extend `write_weekly_digest_report` with:

```python
lines.extend(["", "## Recurring CI Issues", ""])
if not comparison.baseline_available:
    lines.append("- Baseline unavailable; this run establishes the first comparison snapshot.")
for issue in comparison.issues[:3]:
    flaky = " suspected_flaky" if issue.suspected_flaky else ""
    lines.append(
        f"- `{issue.status}`{flaky}: {issue.category} "
        f"({issue.current_count} occurrences) - {issue.example_detail}"
    )
```

Keep the existing weekly digest sections and do not recompute status in the renderer.

- [ ] **Step 5: Run integration and full tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_main.py tests/test_snapshots.py -v`

Expected: all integration tests PASS.

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 6: Commit snapshot/report integration**

```powershell
git add app/main.py app/report.py tests/test_main.py tests/test_snapshots.py
git commit -m "feat: integrate CI trend snapshots into weekly reports"
```

### Task 6: Document the v2 Demo and Complete Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add v2 positioning and lifecycle definitions**

Add sections explaining that pass-rate counts do not identify repeated incidents, then document `new`, `persistent`, `regressed`, `resolved`, and `suspected_flaky` with the fail-success-fail heuristic.

- [ ] **Step 2: Add a local two-snapshot demo**

Document this reproducible flow:

```powershell
python -m app.main --repo owner/repo --days 14 --limit 20 --snapshot-dir outputs/snapshots
python -m app.main --repo owner/repo --days 14 --limit 20 --snapshot-dir outputs/snapshots
Get-Content outputs/snapshots/*.json
Get-Content outputs/weekly_digest.md
```

State that the first run reports `Baseline unavailable` and a later run can classify issues relative to the adjacent snapshot. Do not claim a live demo output without a token and repository access.

- [ ] **Step 3: Add v2 interview talking points and limitations**

Explain deterministic token normalization, SHA-256 fingerprints, compact JSON schema, pure snapshot comparison, and why `suspected_flaky` is a heuristic rather than a confidence score. Explicitly state that full logs are not persisted.

- [ ] **Step 4: Run final verification**

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: all v1 and v2 tests PASS.

Run: `.venv\Scripts\python.exe -m compileall -q app tests`

Expected: exit `0`.

Run: `.venv\Scripts\python.exe -m app.main --help`

Expected: help includes `--snapshot-dir`.

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 5: Commit v2 documentation**

```powershell
git add README.md
git commit -m "docs: document failure trend analysis v2"
```

### Task 7: Final Repository Review

**Files:**
- Modify only files required by final verification.

- [ ] **Step 1: Inspect status and history**

Run: `git status --short` and `git log --oneline -12`.

Expected: only intentional v2 files are changed/untracked and commits are focused.

- [ ] **Step 2: Review scope guardrails**

Run: `rg -n "sqlite|streamlit|flask|fastapi|openai|embedding|slack|feishu" app tests README.md`.

Expected: no new v2 implementation dependency outside the explicitly documented limitation text.

- [ ] **Step 3: Verify README claims against code and tests**

Check that snapshot paths, schema fields, lifecycle statuses, flaky heuristic, and test counts match the implementation and latest command output. Correct any mismatch before the final commit.
