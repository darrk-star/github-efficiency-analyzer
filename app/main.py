from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from app.charts import write_failed_workflow_chart, write_failure_trend_chart
from app.config import AppConfig
from app.github_client import GitHubApiError, GitHubClient
from app.metrics import (
    build_daily_failure_trend,
    build_failed_workflow_breakdown,
    build_pr_rows,
    build_workflow_rows,
    build_weekly_ci_digest,
    summarize_pull_requests,
    summarize_workflow_runs,
    write_rows_to_csv,
)
from app.report import write_markdown_report, write_weekly_digest_report


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def repo_name(value: str) -> str:
    try:
        GitHubClient._split_repo(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must use owner/name form") from exc
    return value


def format_optional_number(value: float | None) -> str:
    return "N/A" if value is None else str(value)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze GitHub pull request efficiency metrics for a repository."
    )
    parser.add_argument(
        "--repo",
        required=True,
        type=repo_name,
        help="GitHub repository in owner/name form.",
    )
    parser.add_argument(
        "--days",
        type=positive_int,
        default=30,
        help="Number of days to look back from now. Default: 30.",
    )
    parser.add_argument(
        "--limit",
        type=positive_int,
        default=100,
        help="Maximum number of pull requests to inspect. Default: 100.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory where CSV and Markdown reports are written.",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(argv)

    try:
        config = AppConfig.from_env()
        client = GitHubClient(config)
        created_after = datetime.now(tz=timezone.utc) - timedelta(days=args.days)

        logging.info("Fetching pull requests for %s", args.repo)
        pr_records = client.fetch_pull_requests(
            repo=args.repo,
            created_after=created_after,
            limit=args.limit,
        )
        logging.info("Fetching workflow runs for %s", args.repo)
        workflow_records = client.fetch_workflow_runs(
            repo=args.repo,
            created_after=created_after,
            limit=args.limit,
        )

        pr_summary = summarize_pull_requests(pr_records)
        workflow_summary = summarize_workflow_runs(workflow_records)
        pr_rows = build_pr_rows(pr_records)
        workflow_rows = build_workflow_rows(workflow_records)
        daily_trend_frame = build_daily_failure_trend(workflow_records)
        failed_workflow_frame = build_failed_workflow_breakdown(workflow_records)
        weekly_digest = build_weekly_ci_digest(workflow_records)

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        pr_csv_path = output_dir / "pull_requests.csv"
        workflow_csv_path = output_dir / "workflow_runs.csv"
        md_path = output_dir / "summary.md"
        weekly_md_path = output_dir / "weekly_digest.md"
        trend_chart_path = output_dir / "ci_failure_trend.png"
        workflow_chart_path = output_dir / "unstable_workflows.png"

        write_rows_to_csv(pr_csv_path, pr_rows)
        write_rows_to_csv(workflow_csv_path, workflow_rows)
        write_markdown_report(md_path, args.repo, args.days, pr_summary, workflow_summary)
        write_weekly_digest_report(weekly_md_path, args.repo, args.days, weekly_digest)
        trend_chart_written = write_failure_trend_chart(daily_trend_frame, trend_chart_path)
        workflow_chart_written = write_failed_workflow_chart(
            failed_workflow_frame, workflow_chart_path
        )

        print(f"Repository: {args.repo}")
        print(f"PRs inspected: {pr_summary.total_prs}")
        print(f"Merged PRs: {pr_summary.merged_prs}")
        print(f"Average merge time (hours): {format_optional_number(pr_summary.avg_merge_hours)}")
        print(f"Workflow runs inspected: {workflow_summary.total_runs}")
        print(
            "Workflow success rate (%): "
            f"{format_optional_number(workflow_summary.success_rate)}"
        )
        print(f"PR CSV report: {pr_csv_path.resolve()}")
        print(f"Workflow CSV report: {workflow_csv_path.resolve()}")
        print(f"Markdown summary: {md_path.resolve()}")
        print(f"Weekly digest: {weekly_md_path.resolve()}")
        print(
            "CI failure trend chart: "
            + (str(trend_chart_path.resolve()) if trend_chart_written else "not generated")
        )
        print(
            "Unstable workflows chart: "
            + (str(workflow_chart_path.resolve()) if workflow_chart_written else "not generated")
        )
        return 0
    except (GitHubApiError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
