# Resume Portfolio Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the GitHub Efficiency Analyzer easier to evaluate as a resume portfolio project without changing its core product scope.

**Architecture:** Keep the existing Python CLI and reporting architecture intact. Improve the repository's first-impression layer in README and metadata, then add focused regression coverage around optional demo chart failures and API boundary behavior.

**Tech Stack:** Python 3.11+, pytest, requests, ruff, mypy, GitHub Actions, Markdown.

---

### Task 1: Portfolio README entry point

**Files:**
- Modify: `README.md`

- [ ] Add CI, Pages, Python, and test-count badges directly below the title.
- [ ] Add a concise Chinese/English-neutral project summary covering problem, approach, and outputs.
- [ ] Add a copyable resume bullet section with measurable engineering details already supported by the repository.
- [ ] Add a four-step 30-second offline demo path and make the live/offline distinction explicit.
- [ ] Keep existing architecture, limitations, and interview talking points intact.

### Task 2: Repository metadata hygiene

**Files:**
- Create: `LICENSE`
- Modify: `.gitignore`

- [ ] Add the MIT License using the repository owner name `darrk-star` and year 2026.
- [ ] Ignore `.storage/` as a local indexing/tool artifact without deleting the existing directory.

### Task 3: Demo chart error boundary

**Files:**
- Modify: `app/demo.py`
- Test: `tests/test_demo.py`

- [ ] Write a failing test proving a chart-specific runtime failure is logged and the demo still emits the HTML report.
- [ ] Replace `except Exception` with a narrow tuple of expected optional chart/rendering exceptions.
- [ ] Run the focused test and then the full demo test module.

### Task 4: API boundary regression tests

**Files:**
- Modify: `tests/test_github_client.py`

- [ ] Add tests for empty workflow payloads, malformed log archives, and invalid retry configuration behavior.
- [ ] Keep tests deterministic using the existing fake session and response fixtures.
- [ ] Run the focused client tests and verify no production behavior changes are needed unless a test exposes a real bug.

### Task 5: Final verification

**Files:**
- No additional files.

- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m compileall -q app tests`.
- [ ] Run `python -m ruff check .`.
- [ ] Run `python -m ruff format --check .`.
- [ ] Run `python -m mypy app`.
- [ ] Run `python -m app.main --demo --output-dir outputs/verification-demo --snapshot-dir outputs/verification-demo/snapshots`.
- [ ] Review `git diff` and `git status --short`, preserving unrelated user changes.
