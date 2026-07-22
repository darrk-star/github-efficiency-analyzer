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
            (
                f"      <p>Last {days} days of pull request throughput, CI "
                "stability, recurring failures, and generated artifacts.</p>"
            ),
            "    </section>",
            _pull_request_section(pr_summary),
            _workflow_section(workflow_summary),
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


def _pull_request_section(pr_summary: PullRequestMetricsSummary) -> str:
    cards = [
        ("Total PRs", pr_summary.total_prs),
        ("Merged PRs", pr_summary.merged_prs),
        ("Open PRs", pr_summary.open_prs),
        ("Average merge time", _fmt_hours(pr_summary.avg_merge_hours)),
        ("Median merge time", _fmt_hours(pr_summary.median_merge_hours)),
        ("Average PR size", _fmt_number(pr_summary.avg_pr_size)),
        ("Average changed files", _fmt_number(pr_summary.avg_changed_files)),
        ("Average comments", _fmt_number(pr_summary.avg_comments)),
    ]
    body = '<div class="cards">' + "".join(_card(label, value) for label, value in cards) + "</div>"
    body += "<h3>Top Authors</h3>"
    body += _pair_list(pr_summary.top_authors, "PRs", "No pull requests found.")
    return _section("Pull Request Metrics", body)


def _workflow_section(workflow_summary: WorkflowMetricsSummary) -> str:
    cards = [
        ("Workflow runs", workflow_summary.total_runs),
        ("Successful runs", workflow_summary.successful_runs),
        ("Failed runs", workflow_summary.failed_runs),
        ("Cancelled runs", workflow_summary.cancelled_runs),
        ("Excluded runs", workflow_summary.excluded_runs),
        ("Workflow success rate", _fmt_percent(workflow_summary.success_rate)),
        ("Average duration", _fmt_minutes(workflow_summary.avg_duration_minutes)),
    ]
    body = '<div class="cards">' + "".join(_card(label, value) for label, value in cards) + "</div>"
    body += "<h3>CI Failure Categories</h3>"
    body += _pair_list(
        workflow_summary.failure_categories,
        "runs",
        "No failed workflow runs found.",
    )
    body += "<h3>Most Frequently Failing Workflows</h3>"
    body += _pair_list(
        workflow_summary.top_failed_workflows,
        "failed runs",
        "No failing workflows found.",
    )
    return _section("CI Metrics", body)


def _digest_section(digest: WeeklyCiDigest) -> str:
    rows = [
        ("Worst day", _format_pair(digest.worst_day, "failures")),
        ("Noisiest category", _format_pair(digest.noisiest_category, "runs")),
        (
            "Most unstable workflow",
            _format_pair(digest.most_unstable_workflow, "failed runs"),
        ),
    ]
    body = '<div class="split">' + "".join(_fact(label, value) for label, value in rows) + "</div>"
    body += "<h3>Repeated Failure Details</h3>"
    body += _pair_list(
        digest.top_failure_details,
        "occurrences",
        "No repeated failure details in the selected window.",
    )
    body += "<h3>Key Risks</h3>"
    body += _list(digest.key_risks, "No major CI risk signal detected.")
    body += "<h3>Recommended Actions</h3>"
    body += _list(digest.recommended_actions, "No immediate action recommended.")
    return _section("Weekly CI Digest", body)


def _recurring_issue_section(comparison: TrendComparison) -> str:
    body = ""
    if not comparison.baseline_available:
        body += (
            '<p class="muted">Baseline unavailable; this run establishes the '
            "first comparison snapshot.</p>"
        )
    if not comparison.issues:
        body += '<p class="muted">No recurring CI issues were detected.</p>'
    else:
        body += '<div class="issues">'
        for issue in comparison.issues:
            flaky = (
                '<span class="badge flaky">suspected flaky</span>' if issue.suspected_flaky else ""
            )
            workflows = ", ".join(issue.workflows) if issue.workflows else "N/A"
            body += (
                '<article class="issue">'
                f'<div><span class="badge">{escape(issue.status)}</span>{flaky}</div>'
                f"<h3>{escape(issue.category)}</h3>"
                f"<p>{escape(issue.example_detail)}</p>"
                "<small>"
                f"previous: {issue.previous_count} | current: {issue.current_count} | "
                f"workflow: {escape(workflows)} | {escape(issue.fingerprint)}"
                "</small>"
                "</article>"
            )
        body += "</div>"
    return _section("Recurring CI Issues", body)


def _charts_section(chart_items: dict[str, Path]) -> str:
    if not chart_items:
        return _section(
            "Charts",
            '<p class="muted">Charts were not generated for this run.</p>',
        )
    body = (
        '<div class="charts">'
        + "".join(
            (
                f'<figure><img src="{_path_attr(path)}" alt="{escape(label)}">'
                f"<figcaption>{escape(label)}</figcaption></figure>"
            )
            for label, path in chart_items.items()
        )
        + "</div>"
    )
    return _section("Charts", body)


def _artifact_section(artifact_links: dict[str, Path]) -> str:
    if not artifact_links:
        return _section(
            "Artifacts",
            '<p class="muted">No artifact links were generated.</p>',
        )
    links = "".join(
        f'<li><a href="{_path_attr(path)}">{escape(label)}</a></li>'
        for label, path in artifact_links.items()
    )
    return _section("Artifacts", f"<ul>{links}</ul>")


def _section(title: str, body: str) -> str:
    return f'<section class="panel"><h2>{escape(title)}</h2>{body}</section>'


def _card(label: str, value: object) -> str:
    return (
        f'<article class="card"><span>{escape(label)}</span>'
        f"<strong>{escape(str(value))}</strong></article>"
    )


def _fact(label: str, value: str) -> str:
    return f"<p><strong>{escape(label)}:</strong> {escape(value)}</p>"


def _list(items: list[str], empty: str) -> str:
    values = items or [empty]
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in values) + "</ul>"


def _pair_list(items: list[tuple[str, int]], unit: str, empty: str) -> str:
    if not items:
        return f'<p class="muted">{escape(empty)}</p>'
    return (
        "<ul>"
        + "".join(f"<li>{escape(label)}: {count} {escape(unit)}</li>" for label, count in items)
        + "</ul>"
    )


def _fmt_number(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


def _fmt_hours(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f} hours"


def _fmt_minutes(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f} minutes"


def _fmt_percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}%"


def _format_pair(value: tuple[str, int] | None, unit: str) -> str:
    return "N/A" if value is None else f"{value[0]} ({value[1]} {unit})"


def _path_attr(path: Path) -> str:
    return escape(path.as_posix(), quote=True)


def _css() -> str:
    return """
    :root {
      color-scheme:light; --ink:#172018; --muted:#617060; --paper:#f7f2e8;
      --panel:#fffaf0; --accent:#2f6f4e; --line:#ded3bf;
    }
    * { box-sizing: border-box; }
    body {
      margin:0; font-family:Georgia, 'Times New Roman', serif; color:var(--ink);
      background:radial-gradient(circle at top left, #d7ead4, transparent 32rem),
        var(--paper);
    }
    .shell { width:min(1120px, calc(100% - 32px)); margin:0 auto; padding:48px 0; }
    .hero {
      border:1px solid var(--line); background:linear-gradient(135deg, #fffdf7, #eaf4df);
      padding:36px; border-radius:28px;
    }
    .hero p { color:var(--muted); margin:0 0 12px; }
    h1 { font-size:clamp(2rem, 7vw, 5rem); line-height:.95; margin:0 0 16px; }
    h2 { margin:0 0 18px; font-size:1.4rem; }
    h3 { margin:18px 0 8px; }
    .panel {
      margin-top:22px; padding:28px; border:1px solid var(--line); border-radius:24px;
      background:rgba(255,250,240,.86); box-shadow:0 18px 60px rgba(50,40,20,.08);
    }
    .cards, .charts, .issues, .split {
      display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:14px;
    }
    .card, .issue, figure {
      margin:0; padding:18px; border:1px solid var(--line); border-radius:18px;
      background:#fffdf8;
    }
    .card span, .muted, small { color:var(--muted); }
    .card strong { display:block; margin-top:8px; font-size:1.8rem; }
    .badge {
      display:inline-block; margin:0 8px 8px 0; padding:5px 10px; border-radius:999px;
      background:var(--accent); color:white; font-size:.78rem; text-transform:uppercase;
      letter-spacing:.04em;
    }
    .flaky { background:#b26a2c; }
    img { max-width:100%; height:auto; border-radius:14px; border:1px solid var(--line); }
    a { color:var(--accent); font-weight:700; }
    li { margin:6px 0; }
    """.strip()
