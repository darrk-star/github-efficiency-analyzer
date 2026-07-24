# Review Response Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure first external review response time for the selected pull requests and expose it in CSV, Markdown, HTML, and the offline demo.

**Architecture:** The GitHub client fetches paginated review events while hydrating each selected PR. A `PullRequestRecord` stores only the earliest qualifying review timestamp and reviewer; pure metrics functions aggregate response times and reviewer counts. Report renderers consume those aggregate values without making HTTP calls.

**Tech Stack:** Python 3.11+, requests, argparse, pytest, Ruff, mypy.

---

### Task 1: Capture first qualifying review events

**Files:**
- Modify: `app/models.py`
- Modify: `app/github_client.py`
- Test: `tests/test_github_client.py`

- [ ] Add optional `first_review_at: datetime | None` and `first_reviewer: str | None` to `PullRequestRecord`.
- [ ] Add `_fetch_pull_request_reviews` to paginate `/pulls/{number}/reviews` with `per_page=100`.
- [ ] Add `_first_external_review` that selects the earliest event from another login with state `APPROVED`, `CHANGES_REQUESTED`, or `COMMENTED`, a `submitted_at` timestamp, and a timestamp not before the PR creation time.
- [ ] Write fake-session tests covering pagination, author reviews, `PENDING`, `DISMISSED`, missing timestamps, timestamps before creation, and earliest valid-review selection.
- [ ] Run `python -m pytest tests/test_github_client.py -q`.

### Task 2: Aggregate review response metrics

**Files:**
- Modify: `app/metrics.py`
- Test: `tests/test_metrics.py`

- [ ] Extend `PullRequestMetricsSummary` with average and median first-review hours, no-review PR count, and top first reviewers.
- [ ] Extend PR CSV rows with `first_review_at`, `first_reviewer`, and `first_review_response_hours`.
- [ ] Write pure-metric tests proving only qualifying PRs contribute to average and median, no-review PRs are counted, and equal reviewer counts sort by login.
- [ ] Run `python -m pytest tests/test_metrics.py -q`.

### Task 3: Render review metrics

**Files:**
- Modify: `app/report.py`
- Modify: `app/html_report.py`
- Test: `tests/test_report.py`
- Test: `tests/test_html_report.py`

- [ ] Add Markdown first-review aggregate lines and a top-first-reviewers section with an explicit empty state.
- [ ] Add HTML cards for average response, median response, and PRs without external review, plus a top-first-reviewers list.
- [ ] Write rendering tests for populated and empty review data.
- [ ] Run `python -m pytest tests/test_report.py tests/test_html_report.py -q`.

### Task 4: Preserve deterministic offline demo and docs

**Files:**
- Modify: `examples/fixtures/portfolio_demo.json`
- Modify: `app/demo.py`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-07-24-review-response-metrics-design.md`
- Test: `tests/test_demo.py`

- [ ] Extend fixture PR objects and parser fields with deterministic first-review values.
- [ ] Update README metrics, API-cost, and interview sections with the review-event semantics.
- [ ] Append an implementation note to the approved design.
- [ ] Run `python -m pytest tests/test_demo.py -q`.

### Task 5: Full verification

**Files:**
- No additional files.

- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m compileall -q app tests`.
- [ ] Run `python -m app.main --help`.
- [ ] Run `python -m ruff check . --no-cache`.
- [ ] Run `python -m ruff format --check .`.
- [ ] Run `python -m mypy app --no-incremental`.
- [ ] Run `python -m app.main --demo --output-dir outputs/verification-review-demo --snapshot-dir outputs/verification-review-demo/snapshots`.
- [ ] Run `git diff --check` and inspect `git status --short` to confirm `.env.example` is excluded.
