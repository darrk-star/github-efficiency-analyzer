from __future__ import annotations

import io
import time
import zipfile
from datetime import datetime, timezone
from typing import Any

import requests

from app.ci_failure_analysis import analyze_failure_log
from app.config import AppConfig
from app.models import PullRequestRecord, WorkflowRunRecord


class GitHubApiError(RuntimeError):
    pass


class GitHubClient:
    def __init__(self, config: AppConfig, session: requests.Session | None = None) -> None:
        self._base_url = config.github_api_base.rstrip("/")
        self._max_retries = config.github_max_retries
        self._retry_backoff_seconds = config.github_retry_backoff_seconds
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "User-Agent": "github-efficiency-analyzer",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        if config.github_token:
            self._session.headers["Authorization"] = f"Bearer {config.github_token}"

    def fetch_pull_requests(
        self,
        repo: str,
        created_after: datetime,
        state: str = "all",
        limit: int = 100,
    ) -> list[PullRequestRecord]:
        owner, name = self._split_repo(repo)
        page = 1
        pr_summaries: list[dict[str, Any]] = []

        while len(pr_summaries) < limit:
            response = self._get(
                f"{self._base_url}/repos/{owner}/{name}/pulls",
                params={
                    "state": state,
                    "sort": "updated",
                    "direction": "desc",
                    "per_page": min(100, limit - len(pr_summaries)),
                    "page": page,
                },
                timeout=30,
            )
            page_items = response.json()
            if not page_items:
                break

            for item in page_items:
                created_at = self._parse_dt(item["created_at"])
                if created_at >= created_after:
                    pr_summaries.append(item)
                if len(pr_summaries) >= limit:
                    break

            page += 1

        return self._hydrate_pull_requests(pr_summaries, owner, name)

    def fetch_workflow_runs(
        self,
        repo: str,
        created_after: datetime,
        limit: int = 100,
    ) -> list[WorkflowRunRecord]:
        owner, name = self._split_repo(repo)
        page = 1
        records: list[WorkflowRunRecord] = []

        while len(records) < limit:
            response = self._get(
                f"{self._base_url}/repos/{owner}/{name}/actions/runs",
                params={
                    "per_page": min(100, limit - len(records)),
                    "page": page,
                },
                timeout=30,
            )
            payload = response.json()
            runs = payload.get("workflow_runs", [])
            if not runs:
                break

            for run in runs:
                created_at = self._parse_dt(run["created_at"])
                if created_at < created_after:
                    return records

                conclusion = (run.get("conclusion") or "").lower()
                jobs: list[dict[str, Any]] = []
                if conclusion in {"success", "neutral", "skipped"}:
                    failure_category, failure_detail, failure_source = "passed", None, "conclusion"
                elif conclusion == "cancelled":
                    failure_category = "cancelled"
                    failure_detail = "Workflow run was cancelled."
                    failure_source = "conclusion"
                elif conclusion == "timed_out":
                    failure_category = "timeout"
                    failure_detail = "Workflow run reached the execution timeout."
                    failure_source = "conclusion"
                else:
                    jobs = self._fetch_run_jobs(owner, name, run["id"])
                    failure_category, failure_detail, failure_source = (
                        self._categorize_workflow_failure(
                            owner=owner,
                            name=name,
                            run=run,
                            jobs=jobs,
                        )
                    )
                records.append(
                    WorkflowRunRecord(
                        id=run["id"],
                        name=run["name"],
                        event=run["event"],
                        status=run["status"],
                        conclusion=run.get("conclusion"),
                        created_at=created_at,
                        updated_at=self._parse_dt(run["updated_at"]),
                        run_started_at=self._parse_optional_dt(run.get("run_started_at")),
                        actor=run["actor"]["login"] if run.get("actor") else "unknown",
                        branch=run["head_branch"] or "unknown",
                        duration_minutes=self._duration_minutes(
                            self._parse_optional_dt(run.get("run_started_at")),
                            self._parse_optional_dt(run.get("updated_at")),
                        ),
                        html_url=run["html_url"],
                        jobs_url=run["jobs_url"],
                        failure_category=failure_category,
                        failure_detail=failure_detail,
                        failure_source=failure_source,
                    )
                )
                if len(records) >= limit:
                    break

            page += 1

        return records

    def _hydrate_pull_requests(
        self, pr_summaries: list[dict[str, Any]], owner: str, name: str
    ) -> list[PullRequestRecord]:
        records: list[PullRequestRecord] = []
        for item in pr_summaries:
            number = item["number"]
            detail = self._get(
                f"{self._base_url}/repos/{owner}/{name}/pulls/{number}",
                timeout=30,
            )
            payload = detail.json()
            reviewer_names = tuple(
                sorted(
                    {
                        reviewer["login"]
                        for reviewer in payload.get("requested_reviewers", [])
                    }
                )
            )
            records.append(
                PullRequestRecord(
                    number=payload["number"],
                    title=payload["title"],
                    author=payload["user"]["login"],
                    state=payload["state"],
                    created_at=self._parse_dt(payload["created_at"]),
                    updated_at=self._parse_dt(payload["updated_at"]),
                    closed_at=self._parse_optional_dt(payload.get("closed_at")),
                    merged_at=self._parse_optional_dt(payload.get("merged_at")),
                    additions=payload["additions"],
                    deletions=payload["deletions"],
                    changed_files=payload["changed_files"],
                    review_comments=payload["review_comments"],
                    comments=payload["comments"],
                    commits=payload["commits"],
                    reviewers=reviewer_names,
                    url=payload["html_url"],
                )
            )
        return records

    def _fetch_run_jobs(self, owner: str, name: str, run_id: int) -> list[dict[str, Any]]:
        response = self._get(
            f"{self._base_url}/repos/{owner}/{name}/actions/runs/{run_id}/jobs",
            params={"per_page": 100},
            timeout=30,
        )
        return response.json().get("jobs", [])

    @staticmethod
    def _split_repo(repo: str) -> tuple[str, str]:
        parts = repo.split("/", maxsplit=1)
        if len(parts) != 2 or not all(parts) or any("/" in part for part in parts):
            raise ValueError("Repository must be in the form owner/name.")
        return parts[0], parts[1]

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)

    @classmethod
    def _parse_optional_dt(cls, value: str | None) -> datetime | None:
        return cls._parse_dt(value) if value else None

    @staticmethod
    def _duration_minutes(started_at: datetime | None, ended_at: datetime | None) -> float | None:
        if not started_at or not ended_at:
            return None
        return round((ended_at - started_at).total_seconds() / 60, 2)

    def _categorize_workflow_failure(
        self,
        owner: str,
        name: str,
        run: dict[str, Any],
        jobs: list[dict[str, Any]],
    ) -> tuple[str, str | None, str]:
        conclusion = (run.get("conclusion") or "").lower()
        if conclusion in {"success", "neutral", "skipped"}:
            return "passed", None, "conclusion"
        if conclusion == "cancelled":
            return "cancelled", "Workflow run was cancelled.", "conclusion"
        if conclusion == "timed_out":
            return "timeout", "Workflow run reached the execution timeout.", "conclusion"

        log_text = self._download_workflow_logs(owner, name, run["id"])
        if log_text:
            analysis = analyze_failure_log(
                log_text=log_text,
                fallback_detail=self._build_failure_detail(jobs),
            )
            return analysis.category, analysis.detail, analysis.source

        fragments: list[str] = [
            str(run.get("name", "")),
            str(run.get("display_title", "")),
        ]
        for job in jobs:
            fragments.append(str(job.get("name", "")))
            fragments.append(str(job.get("conclusion", "")))
            for step in job.get("steps", []):
                fragments.append(str(step.get("name", "")))
                fragments.append(str(step.get("conclusion", "")))
                fragments.append(str(step.get("status", "")))

        haystack = " ".join(part.lower() for part in fragments if part)

        keyword_categories = [
            ("test_failure", ["test", "pytest", "unittest", "integration test", "coverage"]),
            ("lint_failure", ["lint", "flake8", "ruff", "black", "isort", "mypy"]),
            ("build_failure", ["build", "compile", "pack", "bundle"]),
            ("dependency_failure", ["pip", "poetry", "dependency", "install", "resolve"]),
            ("infra_failure", ["docker", "service", "network", "connection", "kubernetes", "container"]),
            ("permission_failure", ["permission", "forbidden", "denied", "unauthorized"]),
        ]

        for category, keywords in keyword_categories:
            if any(keyword in haystack for keyword in keywords):
                return category, self._build_failure_detail(jobs), "job_metadata"

        if conclusion == "failure":
            detail = self._build_failure_detail(jobs)
            return "unknown_failure", detail, "job_metadata" if detail else "fallback"

        detail = self._build_failure_detail(jobs)
        return conclusion or "unknown", detail, "job_metadata" if detail else "fallback"

    def _download_workflow_logs(self, owner: str, name: str, run_id: int) -> str | None:
        try:
            response = self._get(
                f"{self._base_url}/repos/{owner}/{name}/actions/runs/{run_id}/logs",
                allow_redirects=True,
                timeout=60,
            )
        except GitHubApiError:
            return None

        content_type = response.headers.get("Content-Type", "")
        if "application/zip" not in content_type and not response.content.startswith(b"PK"):
            return None

        try:
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                collected: list[str] = []
                for member in archive.namelist():
                    if member.endswith("/"):
                        continue
                    with archive.open(member) as handle:
                        try:
                            collected.append(handle.read().decode("utf-8", errors="ignore"))
                        except OSError:
                            continue
                return "\n".join(collected)
        except zipfile.BadZipFile:
            return None

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

    def _sleep_before_retry(self, attempt: int) -> None:
        time.sleep(self._retry_backoff_seconds * (2**attempt))

    @staticmethod
    def _raise_api_error(response: requests.Response) -> None:
        if response.status_code < 400:
            return

        message = "GitHub API request failed."
        try:
            payload = response.json()
            if isinstance(payload, dict) and payload.get("message"):
                message = str(payload["message"])
        except ValueError:
            if response.text:
                message = response.text[:300]

        if response.status_code == 401:
            raise GitHubApiError(
                "GitHub API authentication failed. Check that GITHUB_TOKEN is valid."
            )
        if (
            response.status_code in {403, 429}
            and response.headers.get("X-RateLimit-Remaining") == "0"
        ):
            reset_value = response.headers.get("X-RateLimit-Reset")
            reset_hint = ""
            if reset_value:
                reset_at = datetime.fromtimestamp(int(reset_value), tz=timezone.utc)
                reset_hint = f" Reset at {reset_at.isoformat()}."
            raise GitHubApiError(f"GitHub API Rate limit exceeded.{reset_hint}")
        if response.status_code == 404:
            raise GitHubApiError("GitHub repository or resource was not found.")
        raise GitHubApiError(f"GitHub API error {response.status_code}: {message}")

    @staticmethod
    def _build_failure_detail(jobs: list[dict[str, Any]]) -> str | None:
        for job in jobs:
            if job.get("conclusion") in {"failure", "timed_out", "cancelled"}:
                step_name = None
                for step in job.get("steps", []):
                    if step.get("conclusion") in {"failure", "timed_out", "cancelled"}:
                        step_name = step.get("name")
                        break
                if step_name:
                    return f"Job '{job.get('name', 'unknown')}' failed at step '{step_name}'."
                return f"Job '{job.get('name', 'unknown')}' concluded with {job.get('conclusion')}."
        return None
