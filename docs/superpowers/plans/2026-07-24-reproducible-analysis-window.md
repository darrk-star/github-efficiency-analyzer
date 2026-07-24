# Reproducible Analysis Window Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional fixed UTC analysis end date so live reports and snapshots are reproducible.

**Architecture:** `--days` remains the window length and `--end-date` becomes the one source of truth for a live run's cutoff. `app.main` resolves one UTC timestamp which drives API collection, snapshot paths, and report metadata. Offline demo data remains fixture-controlled.

**Tech Stack:** Python 3.11+, argparse, pytest, Ruff, mypy.

---

### Task 1: Parse fixed dates

**Files:**
- Modify: `app/main.py`
- Test: `tests/test_main.py`

- [ ] Add `end_date(value: str) -> date`, using `date.fromisoformat`, with an `argparse.ArgumentTypeError` containing `YYYY-MM-DD` for malformed input.
- [ ] Add `--end-date` with `type=end_date` to `parse_args`.
- [ ] Test `parse_args(["--repo", "owner/repo", "--end-date", "2026-07-24"]).end_date == date(2026, 7, 24)`.
- [ ] Test `2026/07/24`, `2026-02-30`, and `not-a-date` each raise the parser type error.
- [ ] Run `python -m pytest tests/test_main.py -q`.

### Task 2: Resolve one live window

**Files:**
- Modify: `app/main.py`
- Test: `tests/test_main.py`

- [ ] Add `_analysis_end_datetime(value: date | None) -> datetime`; a supplied date maps to midnight UTC, an omitted date maps to current UTC time, and a future date raises `ValueError` before collection.
- [ ] Resolve `analysis_end` once in `run`, calculate `created_after = analysis_end - timedelta(days=args.days)`, and use `analysis_end` for `Snapshot.generated_at` and `previous_snapshot_path`.
- [ ] Test a `2026-07-20` end date with 14 days sends `2026-07-06T00:00:00+00:00` to collection and writes `owner__repo__14__2026-07-20.json`.
- [ ] Test a future end date returns exit code 1 before either GitHub collection method runs.
- [ ] Run focused tests, then `python -m pytest tests/test_main.py -q`.

### Task 3: Render cutoff metadata

**Files:**
- Modify: `app/main.py`
- Modify: `app/report.py`
- Modify: `app/html_report.py`
- Modify: `app/demo.py`
- Test: `tests/test_report.py`
- Test: `tests/test_html_report.py`

- [ ] Extend Markdown and HTML report renderer signatures with `analysis_end_date: date`.
- [ ] Render `Analysis end date: 2026-07-20 UTC` in Markdown and `Reporting window ends 2026-07-20 UTC` in HTML.
- [ ] Pass `analysis_end.date()` from live mode and the fixture's current snapshot date from demo mode.
- [ ] Add focused renderer tests and run report, HTML, and demo test modules.

### Task 4: Document and verify

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-07-24-reproducible-analysis-window-design.md`

- [ ] Add the command `python -m app.main --repo microsoft/vscode --days 14 --end-date 2026-07-20` and state that it stabilizes snapshot names and window comparison.
- [ ] Add an implementation note to the specification.
- [ ] Run `python -m pytest -q`, `python -m compileall -q app tests`, `python -m app.main --help`, `python -m ruff check . --no-cache`, `python -m ruff format --check .`, `python -m mypy app --no-incremental`, and `git diff --check`.
- [ ] Run the offline demo and confirm it writes its HTML report and two fixture snapshots.
