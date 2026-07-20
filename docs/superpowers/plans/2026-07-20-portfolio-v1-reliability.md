# Portfolio v1 Reliability Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the CLI into a reliable, well-tested portfolio project for Python backend and engineering productivity roles.

**Architecture:** Preserve the current small-module architecture while centralizing workflow outcome semantics in the domain model and HTTP reliability in `GitHubClient`. Pure metric/report functions consume records produced by the client, and the CLI converts validation and operational failures into concise exit behavior.

**Tech Stack:** Python 3.11, requests, python-dotenv, pandas, matplotlib, pytest, Ruff, mypy, GitHub Actions

---

## File Structure

- Modify `app/models.py`: add shared workflow outcome predicates and failure-analysis provenance fields.
- Modify `app/metrics.py`: consume shared outcome predicates, remove stale DataFrame builders, and expose consistent summary counts.
- Modify `app/ci_failure_analysis.py`: return explainable classification source and avoid generic exit-code misclassification.
- Modify `app/github_client.py`: inject the HTTP session, centralize request/retry/error behavior, correct pagination, and avoid unnecessary requests.
- Modify `app/main.py`: validate CLI values, render zero correctly, and handle known operational errors.
- Modify `app/report.py`: render the expanded, consistent workflow summary.
- Modify `tests/test_metrics.py`: repair stale collection-contract tests and extend metric coverage.
- Create `tests/test_github_client.py`: deterministic HTTP, pagination, retry, and error tests.
- Create `tests/test_main.py`: parser, rendering, and CLI error tests.
- Create `pyproject.toml`: pytest, Ruff, and mypy configuration.
- Create `requirements-dev.txt`: development-only tooling dependencies.
- Create `.github/workflows/ci.yml`: automated lint, type, and test checks.
- Modify `README.md`: portfolio pitch, architecture, metric definitions, verified commands, trade-offs, and limitations.

### Task 1: Restore a Green Baseline and Remove the Stale DataFrame Contract

**Files:**
- Modify: `tests/test_metrics.py`
- Modify: `app/ci_failure_analysis.py`
- Modify: `app/metrics.py`

- [ ] **Step 1: Correct the stale trend and breakdown expectations**

Replace DataFrame indexing in `test_build_weekly_ci_digest_aggregates_trends` with the current row contract:

```python
assert [item["count"] for item in trend] == [2, 1]
assert [item["workflow"] for item in breakdown] == ["CI", "Lint"]
```

- [ ] **Step 2: Run the repaired contract test**

Run: `.venv\Scripts\python.exe -m pytest tests/test_metrics.py::test_build_weekly_ci_digest_aggregates_trends -v`

Expected: PASS, proving the test now matches the public `list[dict]` return contract.

- [ ] **Step 3: Write a failing test for evidence selection by log order**

Update the dependency failure test so it asserts the first matching evidence line in the original log, independent of keyword declaration order:

```python
assert result.category == "dependency_failure"
assert result.detail == (
    "ERROR: Could not find a version that satisfies the requirement "
    "private-package==1.2.3"
)
```

- [ ] **Step 4: Run the evidence test to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_metrics.py::test_analyze_failure_log_detects_dependency_failure -v`

Expected: FAIL because the classifier currently returns the later `No matching distribution` line according to keyword order.

- [ ] **Step 5: Implement first-evidence selection**

In `app/ci_failure_analysis.py`, replace nested keyword-first matching with category matching plus earliest-line extraction:

```python
for category, keywords in patterns:
    if any(keyword in normalized for keyword in keywords):
        return FailureAnalysis(
            category=category,
            detail=_extract_first_matching_detail(log_text, keywords),
        )


def _extract_first_matching_detail(log_text: str, keywords: list[str]) -> str | None:
    for line in log_text.splitlines():
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            return line.strip()[:300]
    return _extract_first_error(log_text)
```

- [ ] **Step 6: Remove unused DataFrame builders**

Delete `build_pr_dataframe` and `build_workflow_dataframe` from `app/metrics.py`. The application and tests use row builders, and retaining two export contracts caused the stale test drift.

- [ ] **Step 7: Run the full existing suite**

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: `5 passed`.

- [ ] **Step 8: Commit the baseline repair**

```powershell
git add app/ci_failure_analysis.py app/metrics.py tests/test_metrics.py
git commit -m "test: restore metrics suite baseline"
```

### Task 2: Centralize Workflow Outcome Semantics

**Files:**
- Modify: `app/models.py`
- Modify: `app/metrics.py`
- Modify: `app/report.py`
- Modify: `tests/test_metrics.py`

- [ ] **Step 1: Write failing model tests for outcome groups**

Add parametrized tests:

```python
import pytest

from app.models import workflow_outcome


@pytest.mark.parametrize(
    ("conclusion", "expected"),
    [
        ("success", "successful"),
        ("failure", "failed"),
        ("timed_out", "failed"),
        ("action_required", "failed"),
        ("cancelled", "cancelled"),
        ("neutral", "excluded"),
        ("skipped", "excluded"),
        ("stale", "excluded"),
        (None, "excluded"),
    ],
)
def test_workflow_outcome_groups_github_conclusions(conclusion, expected):
    assert workflow_outcome(conclusion) == expected
```

- [ ] **Step 2: Run the model test to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_metrics.py::test_workflow_outcome_groups_github_conclusions -v`

Expected: collection ERROR because `workflow_outcome` does not exist.

- [ ] **Step 3: Implement the shared outcome function**

Add to `app/models.py`:

```python
from typing import Literal

WorkflowOutcome = Literal["successful", "failed", "cancelled", "excluded"]


def workflow_outcome(conclusion: str | None) -> WorkflowOutcome:
    normalized = (conclusion or "").lower()
    if normalized == "success":
        return "successful"
    if normalized == "cancelled":
        return "cancelled"
    if normalized in {"neutral", "skipped", "stale", ""}:
        return "excluded"
    return "failed"
```

- [ ] **Step 4: Run the model test to verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_metrics.py::test_workflow_outcome_groups_github_conclusions -v`

Expected: PASS for all nine cases.

- [ ] **Step 5: Write failing aggregation tests for denominator and separate counts**

Extend the workflow summary fixture with neutral and skipped records, then assert:

```python
assert summary.total_runs == 5
assert summary.successful_runs == 1
assert summary.failed_runs == 1
assert summary.cancelled_runs == 1
assert summary.excluded_runs == 2
assert summary.success_rate == 50.0
```

Add a zero-success case:

```python
def test_summarize_workflow_runs_preserves_zero_success_rate():
    summary = summarize_workflow_runs([make_workflow(conclusion="failure")])
    assert summary.success_rate == 0.0
```

- [ ] **Step 6: Run aggregation tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_metrics.py -k "workflow_runs" -v`

Expected: FAIL because the summary lacks separate counters and uses all completed runs as the denominator.

- [ ] **Step 7: Update summary and all failure consumers**

Change `WorkflowMetricsSummary` to:

```python
@dataclass(frozen=True)
class WorkflowMetricsSummary:
    total_runs: int
    successful_runs: int
    failed_runs: int
    cancelled_runs: int
    excluded_runs: int
    success_rate: float | None
    avg_duration_minutes: float | None
    failure_categories: list[tuple[str, int]]
    top_failed_workflows: list[tuple[str, int]]
```

In `summarize_workflow_runs`, group completed records through `workflow_outcome`, calculate the rate only from successful plus failed records, and set it to `None` when that denominator is zero. Update `build_daily_failure_trend`, `build_failed_workflow_breakdown`, and `build_weekly_ci_digest` to include only `workflow_outcome(record.conclusion) == "failed"`.

- [ ] **Step 8: Render the new counts in reports**

In `app/report.py`, add:

```python
f"- Successful workflow runs: {workflow_summary.successful_runs}",
f"- Failed workflow runs: {workflow_summary.failed_runs}",
f"- Cancelled workflow runs: {workflow_summary.cancelled_runs}",
f"- Excluded workflow runs: {workflow_summary.excluded_runs}",
```

- [ ] **Step 9: Run metric tests and full suite**

Run: `.venv\Scripts\python.exe -m pytest tests/test_metrics.py -v`

Expected: all metric tests PASS.

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 10: Commit outcome semantics**

```powershell
git add app/models.py app/metrics.py app/report.py tests/test_metrics.py
git commit -m "fix: unify workflow outcome metrics"
```

### Task 3: Correct Pull Request Pagination

**Files:**
- Create: `tests/test_github_client.py`
- Modify: `app/github_client.py`

- [ ] **Step 1: Add reusable fake HTTP objects**

Create `tests/test_github_client.py` with minimal requests-compatible fakes:

```python
from collections import deque
from datetime import datetime, timezone

from app.config import AppConfig
from app.github_client import GitHubClient


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None, content=b""):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f"unexpected HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses):
        self.headers = {}
        self.responses = deque(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.popleft()
```

- [ ] **Step 2: Write the failing mixed-age pagination test**

Use page one containing an old PR updated recently followed by a new PR, page two containing another new PR, and detail responses for the two matching PRs:

```python
def test_fetch_pull_requests_filters_old_items_without_stopping_pagination():
    session = FakeSession(
        [
            FakeResponse([pr_summary(1, "2026-01-01T00:00:00Z"), pr_summary(2, "2026-07-18T00:00:00Z")]),
            FakeResponse([pr_summary(3, "2026-07-17T00:00:00Z")]),
            FakeResponse([]),
            FakeResponse(pr_detail(2)),
            FakeResponse(pr_detail(3)),
        ]
    )
    client = GitHubClient(AppConfig(), session=session)

    records = client.fetch_pull_requests(
        "owner/repo",
        datetime(2026, 7, 1, tzinfo=timezone.utc),
        limit=2,
    )

    assert [record.number for record in records] == [2, 3]
```

Define `pr_summary(number, created_at)` and `pr_detail(number)` in the same test file with the exact GitHub fields consumed by the client.

- [ ] **Step 3: Run the pagination test to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_github_client.py::test_fetch_pull_requests_filters_old_items_without_stopping_pagination -v`

Expected: FAIL because `GitHubClient` does not accept a session and the existing collector stops at the old PR.

- [ ] **Step 4: Inject a session and correct matching-limit behavior**

Change construction to:

```python
def __init__(self, config: AppConfig, session: requests.Session | None = None) -> None:
    self._session = session or requests.Session()
```

In `fetch_pull_requests`, append only items whose `created_at >= created_after`, do not return when an old item is encountered, and continue paging until `len(pr_summaries) == limit` or the endpoint returns no items.

- [ ] **Step 5: Run the pagination test to verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_github_client.py::test_fetch_pull_requests_filters_old_items_without_stopping_pagination -v`

Expected: PASS with records `[2, 3]`.

- [ ] **Step 6: Add invalid-repository unit coverage**

```python
import pytest


@pytest.mark.parametrize("repo", ["owner", "/repo", "owner/", "owner/repo/extra"])
def test_split_repo_rejects_invalid_values(repo):
    with pytest.raises(ValueError, match="owner/name"):
        GitHubClient._split_repo(repo)
```

Change `_split_repo` to require exactly two non-empty slash-separated components.

- [ ] **Step 7: Run client and full tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_github_client.py -v`

Expected: all client tests PASS.

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 8: Commit pagination fixes**

```powershell
git add app/github_client.py tests/test_github_client.py
git commit -m "fix: collect pull requests across mixed-age pages"
```

### Task 4: Avoid Unnecessary Workflow Requests and Preserve Time-Window Pagination

**Files:**
- Modify: `tests/test_github_client.py`
- Modify: `app/github_client.py`

- [ ] **Step 1: Write a failing successful-run request test**

```python
def test_fetch_workflow_runs_does_not_fetch_jobs_or_logs_for_success():
    session = FakeSession(
        [
            FakeResponse({"workflow_runs": [workflow_run(1, "success")]}),
            FakeResponse({"workflow_runs": []}),
        ]
    )
    client = GitHubClient(AppConfig(), session=session)

    records = client.fetch_workflow_runs(
        "owner/repo",
        datetime(2026, 7, 1, tzinfo=timezone.utc),
        limit=10,
    )

    assert records[0].failure_category == "passed"
    assert len(session.calls) == 2
```

Define `workflow_run(run_id, conclusion, created_at="2026-07-18T00:00:00Z")` with all consumed fields.

- [ ] **Step 2: Run the request test to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_github_client.py::test_fetch_workflow_runs_does_not_fetch_jobs_or_logs_for_success -v`

Expected: FAIL because jobs are currently fetched for every workflow run.

- [ ] **Step 3: Fetch diagnostics only for unsuccessful conclusions**

In `fetch_workflow_runs`, classify `success`, `neutral`, `skipped`, and `cancelled` directly without fetching jobs. For failed outcomes, fetch jobs and pass them to `_categorize_workflow_failure`. Keep timeout conclusion handling direct.

- [ ] **Step 4: Run the request test to verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_github_client.py::test_fetch_workflow_runs_does_not_fetch_jobs_or_logs_for_success -v`

Expected: PASS with exactly the two workflow-list calls.

- [ ] **Step 5: Write a failed-run fallback test**

Supply list, jobs, and a non-ZIP log response, then assert:

```python
assert records[0].failure_category == "test_failure"
assert records[0].failure_detail == "Job 'tests' failed at step 'pytest'."
assert records[0].failure_source == "job_metadata"
```

- [ ] **Step 6: Run the fallback test to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_github_client.py::test_failed_workflow_uses_job_metadata_when_logs_are_unavailable -v`

Expected: FAIL because `failure_source` is not modeled.

- [ ] **Step 7: Add failure provenance**

Extend `WorkflowRunRecord`:

```python
failure_source: str
```

Return `(category, detail, source)` from `_categorize_workflow_failure`, using `conclusion`, `logs`, `job_metadata`, or `fallback`. Add `failure_source` to workflow CSV rows.

- [ ] **Step 8: Add time-window stopping coverage**

Create a workflow page with one matching run followed by an old run. Assert the old run is excluded and no next page is requested. This is valid because GitHub workflow runs are returned newest first by creation time.

- [ ] **Step 9: Run client and full tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_github_client.py -v`

Expected: all workflow collection tests PASS.

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 10: Commit workflow request optimization**

```powershell
git add app/models.py app/github_client.py app/metrics.py tests/test_github_client.py tests/test_metrics.py
git commit -m "perf: limit workflow diagnostic requests"
```

### Task 5: Add Bounded Retries and Actionable GitHub Errors

**Files:**
- Modify: `app/config.py`
- Modify: `app/github_client.py`
- Modify: `tests/test_github_client.py`

- [ ] **Step 1: Write failing retry tests**

Enhance `FakeResponse` with `text` and write:

```python
def test_request_retries_transient_server_error(monkeypatch):
    session = FakeSession([
        FakeResponse({}, status_code=503),
        FakeResponse([]),
    ])
    monkeypatch.setattr("app.github_client.time.sleep", lambda _: None)
    client = GitHubClient(AppConfig(github_max_retries=1), session=session)

    assert client.fetch_pull_requests("owner/repo", cutoff(), limit=1) == []
    assert len(session.calls) == 2


def test_request_does_not_retry_not_found():
    session = FakeSession([FakeResponse({}, status_code=404)])
    client = GitHubClient(AppConfig(github_max_retries=2), session=session)

    with pytest.raises(GitHubApiError, match="not found"):
        client.fetch_pull_requests("owner/repo", cutoff(), limit=1)
    assert len(session.calls) == 1
```

- [ ] **Step 2: Run retry tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_github_client.py -k "retry or not_found" -v`

Expected: collection ERROR because retry configuration and `GitHubApiError` do not exist.

- [ ] **Step 3: Add retry configuration**

Extend `AppConfig`:

```python
github_max_retries: int = 2
github_retry_backoff_seconds: float = 0.25
```

Read optional `GITHUB_MAX_RETRIES` and `GITHUB_RETRY_BACKOFF_SECONDS` values in `from_env`.

- [ ] **Step 4: Centralize GET requests**

Add:

```python
class GitHubApiError(RuntimeError):
    pass


def _get(self, url: str, **kwargs: Any) -> requests.Response:
    for attempt in range(self._max_retries + 1):
        try:
            response = self._session.get(url, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as exc:
            if attempt == self._max_retries:
                raise GitHubApiError(f"GitHub request failed after retries: {exc}") from exc
            self._sleep_before_retry(attempt)
            continue
        if response.status_code in {429, 500, 502, 503, 504} and attempt < self._max_retries:
            self._sleep_before_retry(attempt)
            continue
        self._raise_api_error(response)
        return response
    raise GitHubApiError("GitHub request failed after retries.")
```

Use `_get` for list, detail, jobs, and logs requests. `_raise_api_error` must map `401` to a token hint, `403` with exhausted rate-limit headers to a reset-time message, `404` to a repository/resource-not-found message, and other errors to status plus GitHub's message field.

- [ ] **Step 5: Add rate-limit and authentication tests**

```python
def test_rate_limit_error_includes_reset_time():
    response = FakeResponse(
        {"message": "API rate limit exceeded"},
        status_code=403,
        headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1784563200"},
    )
    with pytest.raises(GitHubApiError, match="Rate limit"):
        GitHubClient(AppConfig(github_max_retries=0), session=FakeSession([response])).fetch_pull_requests(
            "owner/repo", cutoff(), limit=1
        )


def test_authentication_error_mentions_github_token():
    response = FakeResponse({"message": "Bad credentials"}, status_code=401)
    with pytest.raises(GitHubApiError, match="GITHUB_TOKEN"):
        GitHubClient(AppConfig(), session=FakeSession([response])).fetch_pull_requests(
            "owner/repo", cutoff(), limit=1
        )
```

- [ ] **Step 6: Run reliability tests and full suite**

Run: `.venv\Scripts\python.exe -m pytest tests/test_github_client.py -v`

Expected: all API reliability tests PASS.

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 7: Commit HTTP reliability**

```powershell
git add app/config.py app/github_client.py tests/test_github_client.py
git commit -m "feat: add resilient GitHub API requests"
```

### Task 6: Make Failure Classification Explainable

**Files:**
- Modify: `app/ci_failure_analysis.py`
- Modify: `app/github_client.py`
- Modify: `tests/test_metrics.py`
- Modify: `tests/test_github_client.py`

- [ ] **Step 1: Write a failing generic-exit-code test**

```python
def test_generic_exit_code_does_not_claim_test_failure():
    result = analyze_failure_log("Error: Process completed with exit code 1")

    assert result.category == "unknown_failure"
    assert result.source == "fallback"
```

- [ ] **Step 2: Run the classifier test to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_metrics.py::test_generic_exit_code_does_not_claim_test_failure -v`

Expected: FAIL because generic exit code 1 is currently a test-failure signature and `source` is absent.

- [ ] **Step 3: Add classification source and specific-first rules**

Change the result type to:

```python
@dataclass(frozen=True)
class FailureAnalysis:
    category: str
    detail: str | None
    source: str
```

Return `source="logs"` for matched log rules and resource/timeout patterns. Remove `error: process completed with exit code 1` from test keywords. Return `source="fallback"` for unknown results using fallback detail or the first error line.

- [ ] **Step 4: Propagate classifier provenance through the client**

When log analysis succeeds, return `analysis.source` from `_categorize_workflow_failure`. Preserve `job_metadata`, `conclusion`, and `fallback` for non-log branches.

- [ ] **Step 5: Run classification and full tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_metrics.py tests/test_github_client.py -v`

Expected: all classifier and client tests PASS.

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 6: Commit explainable classification**

```powershell
git add app/ci_failure_analysis.py app/github_client.py tests/test_metrics.py tests/test_github_client.py
git commit -m "feat: expose CI classification evidence source"
```

### Task 7: Harden CLI Validation and Error Output

**Files:**
- Modify: `app/main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write failing positive-integer parser tests**

```python
import pytest

from app.main import positive_int


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_positive_int_rejects_invalid_values(value):
    with pytest.raises(Exception):
        positive_int(value)


def test_positive_int_accepts_positive_values():
    assert positive_int("7") == 7
```

- [ ] **Step 2: Run parser tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_main.py -k positive_int -v`

Expected: collection ERROR because `positive_int` does not exist.

- [ ] **Step 3: Implement parser validation**

Add:

```python
def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed
```

Use `type=positive_int` for both `--days` and `--limit`. Add a `repo_name` argparse type that delegates to strict `owner/name` validation without making a network request.

- [ ] **Step 4: Write failing formatting and operational-error tests**

Extract:

```python
def format_optional_number(value: float | None) -> str:
    return "N/A" if value is None else str(value)
```

Test desired behavior before implementation:

```python
def test_format_optional_number_preserves_zero():
    assert format_optional_number(0.0) == "0.0"


def test_run_returns_nonzero_for_github_error(monkeypatch, capsys):
    monkeypatch.setattr("app.main.GitHubClient.fetch_pull_requests", raise_api_error)
    assert run(["--repo", "owner/repo"]) == 1
    assert "GitHub API" in capsys.readouterr().err
```

- [ ] **Step 5: Run formatting/error tests to verify RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_main.py -k "format_optional or github_error" -v`

Expected: collection ERROR because the helper and testable `run` entry point do not exist.

- [ ] **Step 6: Split orchestration into a return-code function**

Change `parse_args` to accept `argv: list[str] | None = None`. Move orchestration into:

```python
def run(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        # Existing collection, aggregation, and output workflow.
        return 0
    except (GitHubApiError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    raise SystemExit(run())
```

Use `format_optional_number` for numeric console output so `0` remains visible.

- [ ] **Step 7: Run CLI and full tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_main.py -v`

Expected: all CLI tests PASS.

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: all tests PASS.

- [ ] **Step 8: Commit CLI hardening**

```powershell
git add app/main.py tests/test_main.py
git commit -m "feat: harden CLI validation and errors"
```

### Task 8: Add Reproducible Quality Tooling and CI

**Files:**
- Create: `pyproject.toml`
- Create: `requirements-dev.txt`
- Create: `.github/workflows/ci.yml`
- Modify: `requirements.txt`
- Modify: `.gitignore`
- Modify: application and test files only where Ruff or mypy reports concrete issues

- [ ] **Step 1: Separate runtime and development dependencies**

Keep runtime dependencies in `requirements.txt`:

```text
python-dotenv>=1.0.1,<2.0.0
requests>=2.32.0,<3.0.0
pandas>=2.2.2,<3.0.0
matplotlib>=3.9.0,<4.0.0
```

Create `requirements-dev.txt`:

```text
-r requirements.txt
pytest>=8.2.0,<9.0.0
ruff>=0.12.0,<1.0.0
mypy>=1.16.0,<2.0.0
types-requests>=2.32.0,<3.0.0
```

- [ ] **Step 2: Add tool configuration**

Create `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.mypy]
python_version = "3.11"
files = ["app"]
check_untyped_defs = true
no_implicit_optional = true
warn_unused_ignores = true
ignore_missing_imports = true
```

- [ ] **Step 3: Install development tools if absent**

Run: `.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`

Expected: dependencies install successfully. If network access is unavailable, request approval and rerun the exact command; do not skip verification.

- [ ] **Step 4: Run Ruff and fix only reported issues**

Run: `.venv\Scripts\python.exe -m ruff check .`

Expected initially: possible import, style, or modernization failures.

Run: `.venv\Scripts\python.exe -m ruff check . --fix`

Review the diff, then run: `.venv\Scripts\python.exe -m ruff format .`

Run: `.venv\Scripts\python.exe -m ruff check .`

Expected: PASS.

- [ ] **Step 5: Run mypy and resolve concrete application errors**

Run: `.venv\Scripts\python.exe -m mypy app`

Expected initially: possible annotations around requests-compatible sessions, chart inputs, or JSON payloads.

Add explicit protocols/type aliases where required; do not silence errors with broad `# type: ignore` comments.

Run: `.venv\Scripts\python.exe -m mypy app`

Expected: PASS.

- [ ] **Step 6: Add GitHub Actions**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  quality:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - run: python -m pip install --upgrade pip
      - run: python -m pip install -r requirements-dev.txt
      - run: python -m ruff check .
      - run: python -m ruff format --check .
      - run: python -m mypy app
      - run: python -m pytest -q
```

- [ ] **Step 7: Ignore local tool caches**

Append to `.gitignore`:

```text
.mypy_cache/
.ruff_cache/
```

- [ ] **Step 8: Run the exact local CI sequence**

Run: `.venv\Scripts\python.exe -m ruff check .`

Run: `.venv\Scripts\python.exe -m ruff format --check .`

Run: `.venv\Scripts\python.exe -m mypy app`

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: every command exits `0`.

- [ ] **Step 9: Commit quality tooling**

```powershell
git add pyproject.toml requirements.txt requirements-dev.txt .gitignore .github/workflows/ci.yml app tests
git commit -m "ci: add lint type and test checks"
```

### Task 9: Rewrite README as a Verifiable Portfolio Case Study

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Capture verified command output**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m mypy app
```

Record only facts established by these commands. Do not add a coverage percentage because coverage measurement is not part of v1.

- [ ] **Step 2: Replace the opening with the portfolio pitch**

Use this positioning:

```markdown
# GitHub Efficiency Analyzer

A Python CLI that turns GitHub pull request and Actions data into explainable engineering-efficiency reports. It demonstrates resilient REST API integration, explicit metric semantics, deterministic CI log classification, typed domain models, and automated quality checks.
```

- [ ] **Step 3: Add architecture and data flow**

Document this flow:

```text
GitHub REST API
  -> resilient collection and pagination
  -> typed PR/workflow records
  -> pure metrics and failure classification
  -> CSV, Markdown, and PNG reports
```

Explain the responsibility of each `app` module in a compact table.

- [ ] **Step 4: Document metric definitions and trade-offs**

State the exact success-rate denominator, outcome exclusions, PR creation-time window, merge-time definition, and rule-based classifier limitation. Explain why v1 favors explainability over an LLM classifier and why the project does not yet claim historical reviewer participation.

- [ ] **Step 5: Add setup, quality, and demo commands**

Include:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m app.main --repo microsoft/vscode --days 14 --limit 20
python -m pytest -q
python -m ruff check .
python -m mypy app
```

Label the existing `microsoft/vscode` numbers as a historical sample rather than guaranteed current output.

- [ ] **Step 6: Add interview talking points and honest limitations**

Include concise sections covering:

- Correctness challenge: PRs sorted by update time but filtered by creation time.
- Performance choice: logs and jobs fetched only when diagnostics need them.
- Reliability choice: bounded retry and actionable rate-limit/auth errors.
- Testing choice: deterministic HTTP fixtures rather than live network tests.
- Limitations: no persistence, no org-wide aggregation, heuristic classification, and no historical review-event metrics.

- [ ] **Step 7: Verify all README commands and paths**

Run: `rg -n "pytest|ruff|mypy|requirements-dev|workflow success|created_at|GITHUB_TOKEN" README.md`

Expected: commands and metric definitions are present and consistent with repository configuration.

Run: `.venv\Scripts\python.exe -m app.main --help`

Expected: help exits `0` and matches documented arguments. Do not require a live GitHub request for this verification.

- [ ] **Step 8: Commit the portfolio documentation**

```powershell
git add README.md
git commit -m "docs: present analyzer as a reliability case study"
```

### Task 10: Final Verification and Repository Review

**Files:**
- Modify only files required to resolve failures found by verification.

- [ ] **Step 1: Run formatting verification**

Run: `.venv\Scripts\python.exe -m ruff format --check .`

Expected: PASS.

- [ ] **Step 2: Run lint verification**

Run: `.venv\Scripts\python.exe -m ruff check .`

Expected: PASS.

- [ ] **Step 3: Run type verification**

Run: `.venv\Scripts\python.exe -m mypy app`

Expected: PASS.

- [ ] **Step 4: Run the complete test suite**

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: all tests PASS with zero failures.

- [ ] **Step 5: Verify CLI entry points**

Run: `.venv\Scripts\python.exe -m app.main --help`

Expected: exit `0` and show `--repo`, `--days`, `--limit`, and `--output-dir`.

Run: `.venv\Scripts\python.exe -m app.main --repo invalid --days 0`

Expected: non-zero exit with argparse validation text and no application traceback.

- [ ] **Step 6: Inspect repository state and diff**

Run: `git status --short`

Expected: only the pre-existing untracked `.storage/` directory, unless the user has made concurrent changes.

Run: `git log --oneline -12`

Expected: focused commits corresponding to the tasks above.

Run: `git diff HEAD~8 --check`

Expected: no whitespace errors. Adjust the commit range if fewer implementation commits were created.

- [ ] **Step 7: Review README claims against evidence**

Confirm manually that every statement about tests, typing, CI, retries, metric semantics, and classification provenance is backed by code and the verification output from Steps 1-5.

- [ ] **Step 8: Create a final fix commit only if verification required changes**

```powershell
git add <only-files-changed-during-final-verification>
git commit -m "fix: resolve final portfolio verification issues"
```

If no files changed, do not create an empty commit.
