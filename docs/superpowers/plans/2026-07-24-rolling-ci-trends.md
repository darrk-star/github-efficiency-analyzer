# Rolling CI Trends Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task.

**Goal:** Add explainable rolling CI failure trends from continuous compatible snapshots.

**Architecture:** Snapshot discovery builds an adjacent oldest-to-newest chain. Pure trend calculation zero-fills issue counts and labels direction, coverage confidence, and flaky signals. CLI, reports, demo, and README consume it without changing current two-window behavior.

**Tech Stack:** Python, pytest, Ruff, mypy, dataclasses, JSON, pathlib.

---

## File Map

- `app/snapshots.py` and `tests/test_snapshots.py`: continuous snapshot lookup.
- `app/trends.py` and `tests/test_trends.py`: rolling models and aggregation.
- `app/main.py`, reports, demo, fixture, README, and corresponding tests: integration and portfolio output.

### Task 1: Continuous Snapshot Discovery

**Files:** Modify `app/snapshots.py`; modify `tests/test_snapshots.py`.

- [ ] Write failing tests for `load_recent_snapshots(directory, current, windows)`: return valid predecessor snapshots oldest-to-newest; stop safely on a missing file, malformed JSON, unsupported schema, repository mismatch, or window mismatch.
- [ ] Run `./.venv/Scripts/python -m pytest tests/test_snapshots.py -q`; expected: import failure for `load_recent_snapshots`.
- [ ] Implement the loader. Start with current snapshot; repeatedly subtract `current.window_days`; resolve with `snapshot_filename`; stop at missing paths, decoding errors, schema errors, or incompatible metadata; reverse before returning. Keep `previous_snapshot_path` unchanged.
- [ ] Run `./.venv/Scripts/python -m pytest tests/test_snapshots.py -q`; expected: PASS.
- [ ] Commit with `git add app/snapshots.py tests/test_snapshots.py` and `git commit -m "feat: load continuous CI snapshots"`.

### Task 2: Pure Trend Calculation

**Files:** Modify `app/trends.py`; modify `tests/test_trends.py`.

- [ ] Write failing tests for zero-filled count sequences such as improving `[5, 3, 1, 0]` and worsening `[1, 2, 4, 7]`; cover all direction states, low/medium/high coverage, newest metadata, multi-window flaky detection, and deterministic ordering.
- [ ] Run `./.venv/Scripts/python -m pytest tests/test_trends.py -q`; expected: import failure for `build_rolling_trends`.
- [ ] Add immutable `RollingTrendIssue` and `RollingTrendComparison`, then implement `build_rolling_trends(snapshots)`. Union fingerprints, zero-fill each window, retain newest issue metadata, reuse `_count_flaky_recurrences`, compare endpoints for direction, and map 1, 2-3, 4+ windows to low, medium, high confidence. Leave `compare_snapshots` unchanged.
- [ ] Run `./.venv/Scripts/python -m pytest tests/test_trends.py -q`; expected: PASS.
- [ ] Commit with `git add app/trends.py tests/test_trends.py` and `git commit -m "feat: calculate rolling CI trends"`.

### Task 3: CLI and Report Integration

**Files:** Modify `app/main.py`, `app/report.py`, `app/html_report.py`, `tests/test_main.py`, `tests/test_report.py`, `tests/test_html_report.py`.

- [ ] Write failing tests: `--trend-windows` defaults to 4, accepts 2 and 8, rejects 1 and 9; ordered history reaches the report writers; flaky worsening `[1, 2, 4, 7]` renders series, direction, confidence, and marker; one window renders `Rolling history is still being collected.`
- [ ] Run `./.venv/Scripts/python -m pytest tests/test_main.py tests/test_report.py tests/test_html_report.py -q`; expected: FAIL.
- [ ] Add a 2-to-8 CLI validator and `--trend-windows`. Discover history and calculate trends before writing current snapshot, retaining current adjacent baseline behavior. Add rolling comparison parameters to writers. Render no more than five sorted trend cards/rows, or a truthful history-collection message; show count series, direction, data-coverage confidence, workflow, and flaky marker; escape HTML values.
- [ ] Run the same test command; expected: PASS.
- [ ] Commit with `git add app/main.py app/report.py app/html_report.py tests/test_main.py tests/test_report.py tests/test_html_report.py` and `git commit -m "feat: report rolling CI trends"`.

### Task 4: Four-Window Offline Demo

**Files:** Modify `app/demo.py`, `examples/fixtures/portfolio_demo.json`, `tests/test_demo.py`.

- [ ] Write failing tests requiring four demo snapshots dated 2026-06-08, 2026-06-22, 2026-07-06, and 2026-07-20, plus rolling trends and high data-coverage confidence in generated reports.
- [ ] Run `./.venv/Scripts/python -m pytest tests/test_demo.py -q`; expected: FAIL.
- [ ] Replace explicit previous/current fixture workflow fields with ordered `workflow_windows`. Build/write four snapshots; compare final two for adjacent status and all four for rolling trends. Use final records for standard metrics and charts. Fixture data must demonstrate improving, worsening, and same-workflow fail-success-fail signals.
- [ ] Run the same test command; expected: PASS.
- [ ] Commit with `git add app/demo.py examples/fixtures/portfolio_demo.json tests/test_demo.py` and `git commit -m "feat: extend demo rolling CI history"`.

### Task 5: Documentation and Full Verification

**Files:** Modify `README.md`.

- [ ] Document `--trend-windows`, strict no-gap discovery, zero-filled series, direction rules, and that data-coverage confidence is not a statistical claim. Update demo steps, limitations, resume, and interview language. Update test total only after final pytest output.
- [ ] Run `./.venv/Scripts/python -m app.main --demo --output-dir outputs/rolling-demo --snapshot-dir outputs/rolling-demo/snapshots`; search both reports for `Rolling CI Trends`, `data coverage confidence`, `worsening`, and `improving`; expected: four snapshots and matching text.
- [ ] Run `./.venv/Scripts/python -m pytest -q; ./.venv/Scripts/python -m ruff check .; ./.venv/Scripts/python -m ruff format --check .; ./.venv/Scripts/python -m mypy app; ./.venv/Scripts/python -m compileall app; git diff --check`; expected: all exit 0.
- [ ] Commit with `git add README.md` and `git commit -m "docs: explain rolling CI trend analysis"`.

Never stage `.env.example`; it is the user's pre-existing local modification.
