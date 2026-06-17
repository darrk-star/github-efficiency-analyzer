from __future__ import annotations

from pathlib import Path

from app.metrics import PullRequestMetricsSummary, WeeklyCiDigest, WorkflowMetricsSummary


def write_markdown_report(
    output_path: Path,
    repo: str,
    days: int,
    pr_summary: PullRequestMetricsSummary,
    workflow_summary: WorkflowMetricsSummary,
) -> None:
    lines = [
        f"# GitHub Repo Efficiency Report: {repo}",
        "",
        f"- Time window: last {days} days",
        "",
        "## Pull Request Metrics",
        "",
        f"- Total PRs: {pr_summary.total_prs}",
        f"- Merged PRs: {pr_summary.merged_prs}",
        f"- Open PRs: {pr_summary.open_prs}",
        f"- Average merge time (hours): {_fmt(pr_summary.avg_merge_hours)}",
        f"- Median merge time (hours): {_fmt(pr_summary.median_merge_hours)}",
        f"- Average PR size (lines changed): {_fmt(pr_summary.avg_pr_size)}",
        f"- Average changed files: {_fmt(pr_summary.avg_changed_files)}",
        f"- Average total comments: {_fmt(pr_summary.avg_comments)}",
        "",
        "## CI Metrics",
        "",
        f"- Total workflow runs: {workflow_summary.total_runs}",
        f"- Failed workflow runs: {workflow_summary.failed_runs}",
        f"- Workflow success rate (%): {_fmt(workflow_summary.success_rate)}",
        f"- Average workflow duration (minutes): {_fmt(workflow_summary.avg_duration_minutes)}",
        "",
        "## Top Authors",
        "",
    ]

    if pr_summary.top_authors:
        lines.extend(f"- {author}: {count} PRs" for author, count in pr_summary.top_authors)
    else:
        lines.append("- No pull requests found in the selected window.")

    lines.extend(["", "## CI Failure Categories", ""])
    if workflow_summary.failure_categories:
        lines.extend(
            f"- {category}: {count} runs"
            for category, count in workflow_summary.failure_categories
        )
    else:
        lines.append("- No failed workflow runs found in the selected window.")

    lines.extend(["", "## Most Frequently Failing Workflows", ""])
    if workflow_summary.top_failed_workflows:
        lines.extend(
            f"- {name}: {count} failed runs"
            for name, count in workflow_summary.top_failed_workflows
        )
    else:
        lines.append("- No failing workflows found in the selected window.")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_weekly_digest_report(
    output_path: Path,
    repo: str,
    days: int,
    digest: WeeklyCiDigest,
) -> None:
    lines = [
        f"# Weekly CI Digest: {repo}",
        "",
        f"- Window: last {days} days",
        f"- Worst day: {_format_pair(digest.worst_day, 'failures')}",
        f"- Noisiest failure category: {_format_pair(digest.noisiest_category, 'runs')}",
        f"- Most unstable workflow: {_format_pair(digest.most_unstable_workflow, 'failed runs')}",
        "",
        "## Repeated Failure Details",
        "",
    ]

    if digest.top_failure_details:
        lines.extend(f"- {detail} ({count})" for detail, count in digest.top_failure_details)
    else:
        lines.append("- No repeated failure details in the selected window.")

    lines.extend(["", "## Key Risks", ""])
    if digest.key_risks:
        lines.extend(f"- {risk}" for risk in digest.key_risks)
    else:
        lines.append("- No major CI risk signal detected in the selected window.")

    lines.extend(["", "## Recommended Actions", ""])
    if digest.recommended_actions:
        lines.extend(f"- {action}" for action in digest.recommended_actions)
    else:
        lines.append("- No immediate action recommended.")

    lines.extend(["", "## Repeated Issue Commentary", ""])
    if digest.repeated_issue_commentary:
        lines.extend(f"- {item}" for item in digest.repeated_issue_commentary)
    else:
        lines.append("- No repeated issue commentary available.")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fmt(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "N/A"


def _format_pair(value: tuple[str, int] | None, unit: str) -> str:
    if value is None:
        return "N/A"
    return f"{value[0]} ({value[1]} {unit})"
