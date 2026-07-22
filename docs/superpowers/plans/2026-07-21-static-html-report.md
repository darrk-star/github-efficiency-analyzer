# Static HTML Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single static `index.html` report that makes the existing CSV, Markdown, PNG, and snapshot outputs easy to browse as one portfolio artifact.

**Architecture:** Add a focused `app/html_report.py` presentation module that renders already-computed summaries, digest data, trend comparison data, and artifact links. Keep data collection, metrics, snapshots, charts, and Markdown generation unchanged. Wire the HTML writer into both demo mode and live CLI mode after the existing artifacts are produced.

**Tech Stack:** Python standard library only (`html`, `pathlib`), existing typed metric and trend objects, pytest, current CLI.

---

## File Structure

- Create `app/html_report.py`: deterministic HTML rendering and file writing.
- Create `tests/test_html_report.py`: direct report rendering tests against real metric and trend objects.
- Modify `app/demo.py`: write `index.html` for fixture-backed offline demo and include it in returned paths.
- Modify `app/main.py`: write `index.html` for live analysis and print the path.
- Modify `tests/test_demo.py`: assert demo mode writes and returns `index.html`.
- Modify `tests/test_main.py`: assert live and demo CLI output mention the HTML report.
- Modify `README.md`: document `index.html`, describe it as the best portfolio entry point, and fix malformed demo/failure-trend code fences.

---

### Task 1: HTML Report Renderer

**Files:**
- Create: `app/html_report.py`
- Create: `tests/test_html_report.py`

- [ ] **Step 1: Write failing HTML writer tests**

Add `tests/test_html_report.py` with tests that construct real summary and trend objects and assert on generated HTML text:

```python
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.html_report import write_html_report
from app.metrics import (
    PullRequestMetricsSummary,
    WeeklyCiDigest,
    WorkflowMetricsSummary,
)
from app.snapshots import FailureIssue
from app.trends import TrendComparison, TrendIssue


def test_write_html_report_renders_metrics_statuses_and_artifact_links(tmp_path):
    output_path = tmp_path / "index.html"

    write_html_report(
        output_path=output_path,
        repo="owner/repo",
        days=14,
        pr_summary=PullRequestMetricsSummary(
            total_prs=8,
            merged_prs=5,
            open_prs=3,
            avg_merge_hours=6.5,
            median_merge_hours=4.0,
            avg_pr_size=120.0,
            avg_changed_files=4.5,
            avg_comments=2.0,
            top_authors=[("alice", 5), ("bob", 3)],
        ),
        workflow_summary=WorkflowMetricsSummary(
            total_runs=20,
            successful_runs=14,
            failed_runs=5,
            cancelled_runs=1,
            excluded_runs=0,
            success_rate=73.68,
            avg_duration_minutes=9.25,
            failure_categories=[("test_failure", 3), ("build_failure", 2)],
            top_failed_workflows=[("CI", 4), ("Release", 1)],
        ),
        digest=WeeklyCiDigest(
            worst_day=("2026-07-20", 3),
            noisiest_category=("test_failure", 3),
            most_unstable_workflow=("CI", 4),
            top_failure_details=[("pytest failed", 3)],
            key_risks=["CI has repeated test failures."],
            recommended_actions=["Stabilize the flaky checkout test."],
            repeated_issue_commentary=["`regressed`: test_failure (3 occurrences) - pytest failed"],
        ),
        comparison=TrendComparison(
            baseline_available=True,
            issues=[
                TrendIssue(
                    fingerprint="ci-failure-abc123",
                    category="test_failure",
                    example_detail="pytest failed <danger>",
                    previous_count=1,
                    current_count=3,
                    status="regressed",
                    suspected_flaky=True,
                ),
                TrendIssue(
                    fingerprint="ci-failure-def456",
                    category="build_failure",
                    example_detail="npm build failed",
                    previous_count=2,
                    current_count=0,
                    status="resolved",
                    suspected_flaky=False,
                ),
            ],
        ),
        artifact_links={
            "Pull request CSV": Path("pull_requests.csv"),
            "Workflow CSV": Path("workflow_runs.csv"),
            "Markdown summary": Path("summary.md"),
            "Weekly digest": Path("weekly_digest.md"),
            "Failure trend chart": Path("ci_failure_trend.png"),
            "Snapshot": Path("snapshots/owner__repo__14__2026-07-20.json"),
        },
    )

    html = output_path.read_text(encoding="utf-8")
    assert "<!doctype html>" in html
    assert "owner/repo" in html
    assert "Pull Request Metrics" in html
    assert "Workflow success rate" in html
    assert "Recurring CI Issues" in html
    assert "regressed" in html
    assert "suspected flaky" in html
    assert "resolved" in html
    assert "pytest failed &lt;danger&gt;" in html
    assert 'href="pull_requests.csv"' in html
    assert 'src="ci_failure_trend.png"' in html


def test_write_html_report_handles_missing_baseline_and_optional_artifacts(tmp_path):
    output_path = tmp_path / "index.html"

    write_html_report(
        output_path=output_path,
        repo="owner/repo",
        days=7,
        pr_summary=PullRequestMetricsSummary(0, 0, 0, None, None, None, None, None, []),
        workflow_summary=WorkflowMetricsSummary(0, 0, 0, 0, 0, None, None, [], []),
        digest=WeeklyCiDigest(None, None, None, [], [], [], []),
        comparison=TrendComparison(baseline_available=False, issues=[]),
        artifact_links={},
    )

    html = output_path.read_text(encoding="utf-8")
    assert "Baseline unavailable" in html
    assert "No recurring CI issues" in html
    assert "No artifact links were generated" in html
```

- [ ] **Step 2: Run test to verify RED**

Run:

```powershell
python -m pytest tests/test_html_report.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.html_report'`.

- [ ] **Step 3: Implement minimal HTML report writer**

Create `app/html_report.py`:

```python
from __future__ import annotations

from html import escape
from pathlib import Path

from app.metrics import PullRequestMetricsSummary, WeeklyCiDigest, WorkflowMetricsSummary
from app.trends import TrendComparison


def write_html_report(
    output_path: Path,
    repo: str,
    days: int,
    pr_summary: PullRequestMetricsSummary,
    workflow_summary: WorkflowMetricsSummary,
    digest: WeeklyCiDigest,
    comparison: TrendComparison,
    artifact_links: dict[str, Path],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_html_report(
            repo=repo,
            days=days,
            pr_summary=pr_summary,
            workflow_summary=workflow_summary,
            digest=digest,
            comparison=comparison,
            artifact_links=artifact_links,
        ),
        encoding="utf-8",
    )


def render_html_report(
    repo: str,
    days: int,
    pr_summary: PullRequestMetricsSummary,
    workflow_summary: WorkflowMetricsSummary,
    digest: WeeklyCiDigest,
    comparison: TrendComparison,
    artifact_links: dict[str, Path],
) -> str:
    chart_items = {
        label: path
        for label, path in artifact_links.items()
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".webp"}
    }
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            f"  <title>GitHub Efficiency Report - {escape(repo)}</title>",
            f"  <style>{_css()}</style>",
            "</head>",
            "<body>",
            '  <main class="shell">',
            '    <section class="hero">',
            "      <p>Portfolio report</p>",
            f"      <h1>{escape(repo)}</h1>",
            f"      <p>Last {days} days of pull request throughput, CI stability, recurring failures, and generated artifacts.</p>",
            "    </section>",
            _metrics_section(pr_summary, workflow_summary),
            _digest_section(digest),
            _recurring_issue_section(comparison),
            _charts_section(chart_items),
            _artifact_section(artifact_links),
            "  </main>",
            "</body>",
            "</html>",
            "",
        ]
    )
```

Complete helper functions in the same file:

```python
def _metrics_section(pr_summary: PullRequestMetricsSummary, workflow_summary: WorkflowMetricsSummary) -> str:
    cards = [
        ("Total PRs", pr_summary.total_prs),
        ("Merged PRs", pr_summary.merged_prs),
        ("Average merge time", _fmt_hours(pr_summary.avg_merge_hours)),
        ("Workflow runs", workflow_summary.total_runs),
        ("Failed runs", workflow_summary.failed_runs),
        ("Workflow success rate", _fmt_percent(workflow_summary.success_rate)),
    ]
    return _section("Metrics", '<div class="cards">' + "".join(_card(label, value) for label, value in cards) + "</div>")


def _digest_section(digest: WeeklyCiDigest) -> str:
    rows = [
        ("Worst day", _format_pair(digest.worst_day, "failures")),
        ("Noisiest category", _format_pair(digest.noisiest_category, "runs")),
        ("Most unstable workflow", _format_pair(digest.most_unstable_workflow, "failed runs")),
    ]
    lists = [
        ("Key risks", digest.key_risks, "No major CI risk signal detected."),
        ("Recommended actions", digest.recommended_actions, "No immediate action recommended."),
    ]
    body = '<div class="split">' + "".join(_fact(label, value) for label, value in rows) + "</div>"
    body += "".join(f"<h3>{escape(title)}</h3>{_list(items, empty)}" for title, items, empty in lists)
    return _section("Weekly CI Digest", body)


def _recurring_issue_section(comparison: TrendComparison) -> str:
    body = ""
    if not comparison.baseline_available:
        body += '<p class="muted">Baseline unavailable; this run establishes the first comparison snapshot.</p>'
    if not comparison.issues:
        body += '<p class="muted">No recurring CI issues were detected.</p>'
    else:
        body += '<div class="issues">'
        for issue in comparison.issues:
            flaky = '<span class="badge flaky">suspected flaky</span>' if issue.suspected_flaky else ""
            body += (
                '<article class="issue">'
                f'<div><span class="badge">{escape(issue.status)}</span>{flaky}</div>'
                f"<h3>{escape(issue.category)}</h3>"
                f"<p>{escape(issue.example_detail)}</p>"
                f"<small>previous: {issue.previous_count} | current: {issue.current_count} | {escape(issue.fingerprint)}</small>"
                "</article>"
            )
        body += "</div>"
    return _section("Recurring CI Issues", body)


def _charts_section(chart_items: dict[str, Path]) -> str:
    if not chart_items:
        return _section("Charts", '<p class="muted">Charts were not generated for this run.</p>')
    body = '<div class="charts">' + "".join(
        f'<figure><img src="{escape(path.as_posix())}" alt="{escape(label)}"><figcaption>{escape(label)}</figcaption></figure>'
        for label, path in chart_items.items()
    ) + "</div>"
    return _section("Charts", body)


def _artifact_section(artifact_links: dict[str, Path]) -> str:
    if not artifact_links:
        return _section("Artifacts", '<p class="muted">No artifact links were generated.</p>')
    links = "".join(
        f'<li><a href="{escape(path.as_posix())}">{escape(label)}</a></li>'
        for label, path in artifact_links.items()
    )
    return _section("Artifacts", f"<ul>{links}</ul>")
```

Add formatting helpers and CSS in `app/html_report.py`:

```python
def _section(title: str, body: str) -> str:
    return f'<section class="panel"><h2>{escape(title)}</h2>{body}</section>'


def _card(label: str, value: object) -> str:
    return f'<article class="card"><span>{escape(label)}</span><strong>{escape(str(value))}</strong></article>'


def _fact(label: str, value: str) -> str:
    return f'<p><strong>{escape(label)}:</strong> {escape(value)}</p>'


def _list(items: list[str], empty: str) -> str:
    values = items or [empty]
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in values) + "</ul>"


def _fmt_hours(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f} hours"


def _fmt_percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}%"


def _format_pair(value: tuple[str, int] | None, unit: str) -> str:
    return "N/A" if value is None else f"{value[0]} ({value[1]} {unit})"


def _css() -> str:
    return """
    :root { color-scheme: light; --ink:#172018; --muted:#617060; --paper:#f7f2e8; --panel:#fffaf0; --accent:#2f6f4e; --line:#ded3bf; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: Georgia, 'Times New Roman', serif; color:var(--ink); background: radial-gradient(circle at top left, #d7ead4, transparent 32rem), var(--paper); }
    .shell { width:min(1120px, calc(100% - 32px)); margin:0 auto; padding:48px 0; }
    .hero { border:1px solid var(--line); background:linear-gradient(135deg, #fffdf7, #eaf4df); padding:36px; border-radius:28px; }
    .hero p { color:var(--muted); margin:0 0 12px; }
    h1 { font-size:clamp(2rem, 7vw, 5rem); line-height:.95; margin:0 0 16px; }
    h2 { margin:0 0 18px; font-size:1.4rem; }
    h3 { margin:18px 0 8px; }
    .panel { margin-top:22px; padding:28px; border:1px solid var(--line); border-radius:24px; background:rgba(255,250,240,.86); box-shadow:0 18px 60px rgba(50,40,20,.08); }
    .cards, .charts, .issues, .split { display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:14px; }
    .card, .issue, figure { margin:0; padding:18px; border:1px solid var(--line); border-radius:18px; background:#fffdf8; }
    .card span, .muted, small { color:var(--muted); }
    .card strong { display:block; margin-top:8px; font-size:1.8rem; }
    .badge { display:inline-block; margin:0 8px 8px 0; padding:5px 10px; border-radius:999px; background:var(--accent); color:white; font-size:.78rem; text-transform:uppercase; letter-spacing:.04em; }
    .flaky { background:#b26a2c; }
    img { max-width:100%; height:auto; border-radius:14px; border:1px solid var(--line); }
    a { color:var(--accent); font-weight:700; }
    li { margin:6px 0; }
    """.strip()
```

- [ ] **Step 4: Run test to verify GREEN**

Run:

```powershell
python -m pytest tests/test_html_report.py -q
```

Expected: PASS.

---

### Task 2: Demo and Live CLI Integration

**Files:**
- Modify: `app/demo.py`
- Modify: `app/main.py`
- Modify: `tests/test_demo.py`
- Modify: `tests/test_main.py`

- [ ] **Step 1: Write failing integration tests**

Update `tests/test_demo.py`:

```python
assert output_dir / "index.html" in paths
html = (output_dir / "index.html").read_text(encoding="utf-8")
assert "acme/checkout-service" in html
assert "Recurring CI Issues" in html
```

Update `tests/test_main.py` in `test_run_writes_snapshot_and_weekly_digest_with_missing_baseline`:

```python
html = (tmp_path / "outputs" / "index.html").read_text(encoding="utf-8")
assert "owner/repo" in html
assert "Baseline unavailable" in html
assert "HTML report: " in capsys.readouterr().out
```

Update `test_run_demo_mode_does_not_use_github_client`:

```python
captured = capsys.readouterr()
assert "index.html" in captured.out
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/test_demo.py tests/test_main.py -q
```

Expected: FAIL because `index.html` is not yet written or printed.

- [ ] **Step 3: Wire HTML report into demo mode**

Modify `app/demo.py`:

```python
from app.html_report import write_html_report
```

After defining artifact paths, add:

```python
html_path = output_dir / "index.html"
```

After chart generation, create artifact links and write the HTML:

```python
artifact_links = {
    "Pull request CSV": Path("pull_requests.csv"),
    "Workflow CSV": Path("workflow_runs.csv"),
    "Markdown summary": Path("summary.md"),
    "Weekly digest": Path("weekly_digest.md"),
    "Previous snapshot": previous_snapshot_path.relative_to(output_dir)
    if previous_snapshot_path.is_relative_to(output_dir)
    else previous_snapshot_path,
    "Current snapshot": current_snapshot_path.relative_to(output_dir)
    if current_snapshot_path.is_relative_to(output_dir)
    else current_snapshot_path,
}
for chart_path in chart_paths:
    artifact_links[chart_path.stem.replace("_", " ").title()] = chart_path.name
write_html_report(
    html_path,
    fixture.repo,
    fixture.days,
    pr_summary,
    workflow_summary,
    weekly_digest,
    comparison,
    artifact_links,
)
```

Include `html_path` in `written_paths`.

- [ ] **Step 4: Wire HTML report into live mode**

Modify `app/main.py`:

```python
from app.html_report import write_html_report
```

After existing path definitions:

```python
html_path = output_dir / "index.html"
```

After chart generation:

```python
artifact_links = {
    "Pull request CSV": Path("pull_requests.csv"),
    "Workflow CSV": Path("workflow_runs.csv"),
    "Markdown summary": Path("summary.md"),
    "Weekly digest": Path("weekly_digest.md"),
    "Snapshot": Path(args.snapshot_dir).resolve().relative_to(output_dir.resolve())
    if Path(args.snapshot_dir).resolve().is_relative_to(output_dir.resolve())
    else snapshot_path,
}
if trend_chart_written:
    artifact_links["CI failure trend chart"] = Path("ci_failure_trend.png")
if workflow_chart_written:
    artifact_links["Unstable workflows chart"] = Path("unstable_workflows.png")
write_html_report(
    html_path,
    args.repo,
    args.days,
    pr_summary,
    workflow_summary,
    weekly_digest,
    comparison,
    artifact_links,
)
```

Print:

```python
print(f"HTML report: {html_path.resolve()}")
```

- [ ] **Step 5: Run integration tests to verify GREEN**

Run:

```powershell
python -m pytest tests/test_html_report.py tests/test_demo.py tests/test_main.py -q
```

Expected: PASS.

---

### Task 3: README Documentation and Formatting Cleanup

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update output list**

Add `index.html` to the default outputs:

```markdown
- `index.html` - the best single artifact to open during a portfolio review
```

- [ ] **Step 2: Update offline demo section**

Use this PowerShell example:

```markdown
```powershell
python -m app.main --demo --output-dir outputs/demo --snapshot-dir outputs/demo/snapshots
Start-Process outputs/demo/index.html
Get-Content outputs/demo/weekly_digest.md
Get-Content outputs/demo/snapshots/*.json
```

The demo writes `outputs/demo/index.html`, which is the recommended first file to open when showing the project without GitHub credentials.
```

- [ ] **Step 3: Fix failure trend code fence**

Ensure the section closes the PowerShell code block before explanatory prose:

```markdown
```powershell
python -m app.main --repo owner/repo --days 14 --limit 20 --snapshot-dir outputs/snapshots
# Run again after the next adjacent 14-day window to compare against the prior snapshot:
python -m app.main --repo owner/repo --days 14 --limit 20 --snapshot-dir outputs/snapshots
Get-Content outputs/snapshots/owner__repo__14__*.json
```
```

- [ ] **Step 4: Add project structure entry**

Add:

```text
    html_report.py
```

Add:

```text
    test_html_report.py
```

- [ ] **Step 5: Run README formatting check**

Run:

```powershell
git diff --check
```

Expected: no whitespace errors.

---

### Task 4: Full Verification and Commit

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run targeted tests**

Run:

```powershell
python -m pytest tests/test_html_report.py tests/test_demo.py tests/test_main.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full test suite**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Run compile check**

Run:

```powershell
python -m compileall -q app tests
```

Expected: no output and exit code 0.

- [ ] **Step 4: Run CLI help**

Run:

```powershell
python -m app.main --help
```

Expected: help text includes `--demo`, `--snapshot-dir`, and `--output-dir`.

- [ ] **Step 5: Run offline demo**

Run:

```powershell
python -m app.main --demo --output-dir outputs/demo --snapshot-dir outputs/demo/snapshots
```

Expected: output includes `Offline demo: acme/checkout-service` and an absolute path ending in `outputs\demo\index.html`.

- [ ] **Step 6: Inspect generated HTML**

Run:

```powershell
Get-Content outputs/demo/index.html | Select-Object -First 20
```

Expected: includes `<!doctype html>`, `acme/checkout-service`, and `Portfolio report`.

- [ ] **Step 7: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected: no output and exit code 0.

- [ ] **Step 8: Commit implementation**

Run:

```powershell
git add app/html_report.py app/demo.py app/main.py tests/test_html_report.py tests/test_demo.py tests/test_main.py README.md
git commit -m "feat: add static html report output"
```

Expected: commit succeeds.

