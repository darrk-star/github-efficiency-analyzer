from __future__ import annotations

from collections import deque
from datetime import UTC, datetime

import pytest

from app.config import AppConfig
from app.github_client import GitHubClient


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None, content=b"", text=""):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content
        self.text = text or str(payload)

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


def pr_summary(number: int, created_at: str) -> dict[str, object]:
    return {"number": number, "created_at": created_at}


def pr_detail(number: int) -> dict[str, object]:
    created_at = f"2026-07-{20 - number:02d}T00:00:00Z"
    return {
        "number": number,
        "title": f"PR {number}",
        "user": {"login": "alice"},
        "state": "closed",
        "created_at": created_at,
        "updated_at": created_at,
        "closed_at": created_at,
        "merged_at": created_at,
        "additions": 10,
        "deletions": 2,
        "changed_files": 1,
        "review_comments": 1,
        "comments": 0,
        "commits": 1,
        "requested_reviewers": [],
        "html_url": f"https://example.com/pulls/{number}",
    }


def workflow_run(
    run_id: int,
    conclusion: str,
    created_at: str = "2026-07-18T00:00:00Z",
) -> dict[str, object]:
    return {
        "id": run_id,
        "name": "CI",
        "display_title": "CI",
        "event": "pull_request",
        "status": "completed",
        "conclusion": conclusion,
        "created_at": created_at,
        "updated_at": created_at,
        "run_started_at": created_at,
        "actor": {"login": "alice"},
        "head_branch": "main",
        "html_url": f"https://example.com/runs/{run_id}",
        "jobs_url": f"https://api.example.com/runs/{run_id}/jobs",
    }


def test_fetch_pull_requests_filters_old_items_without_stopping_pagination():
    session = FakeSession(
        [
            FakeResponse(
                [
                    pr_summary(1, "2026-01-01T00:00:00Z"),
                    pr_summary(2, "2026-07-18T00:00:00Z"),
                ]
            ),
            FakeResponse([pr_summary(3, "2026-07-17T00:00:00Z")]),
            FakeResponse(pr_detail(2)),
            FakeResponse(pr_detail(3)),
        ]
    )
    client = GitHubClient(AppConfig(), session=session)

    records = client.fetch_pull_requests(
        "owner/repo",
        datetime(2026, 7, 1, tzinfo=UTC),
        limit=2,
    )

    assert [record.number for record in records] == [2, 3]


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
        datetime(2026, 7, 1, tzinfo=UTC),
        limit=10,
    )

    assert records[0].failure_category == "passed"
    assert len(session.calls) == 2


def test_failed_workflow_uses_job_metadata_when_logs_are_unavailable():
    jobs = {
        "jobs": [
            {
                "name": "tests",
                "conclusion": "failure",
                "steps": [{"name": "pytest", "conclusion": "failure", "status": "completed"}],
            }
        ]
    }
    session = FakeSession(
        [
            FakeResponse({"workflow_runs": [workflow_run(2, "failure")]}),
            FakeResponse(jobs),
            FakeResponse({}, content=b"plain text"),
            FakeResponse({"workflow_runs": []}),
        ]
    )
    client = GitHubClient(AppConfig(), session=session)

    records = client.fetch_workflow_runs(
        "owner/repo",
        datetime(2026, 7, 1, tzinfo=UTC),
        limit=10,
    )

    assert records[0].failure_category == "test_failure"
    assert records[0].failure_detail == "Job 'tests' failed at step 'pytest'."
    assert records[0].failure_source == "job_metadata"


def test_fetch_workflow_runs_stops_at_creation_time_boundary():
    session = FakeSession(
        [
            FakeResponse(
                {
                    "workflow_runs": [
                        workflow_run(1, "success"),
                        workflow_run(2, "success", "2026-06-01T00:00:00Z"),
                    ]
                }
            )
        ]
    )
    client = GitHubClient(AppConfig(), session=session)

    records = client.fetch_workflow_runs(
        "owner/repo",
        datetime(2026, 7, 1, tzinfo=UTC),
        limit=10,
    )

    assert [record.id for record in records] == [1]
    assert len(session.calls) == 1


def test_fetch_workflow_runs_returns_empty_for_empty_payload():
    client = GitHubClient(AppConfig(), session=FakeSession([FakeResponse({})]))

    assert client.fetch_workflow_runs("owner/repo", cutoff(), limit=10) == []


def test_failed_workflow_uses_metadata_when_log_archive_is_malformed():
    jobs = {
        "jobs": [
            {
                "name": "build",
                "conclusion": "failure",
                "steps": [{"name": "compile", "conclusion": "failure"}],
            }
        ]
    }
    session = FakeSession(
        [
            FakeResponse({"workflow_runs": [workflow_run(3, "failure")]}),
            FakeResponse(jobs),
            FakeResponse({}, headers={"Content-Type": "application/zip"}, content=b"not-a-zip"),
            FakeResponse({"workflow_runs": []}),
        ]
    )

    records = GitHubClient(AppConfig(), session=session).fetch_workflow_runs(
        "owner/repo", cutoff(), limit=10
    )

    assert records[0].failure_category == "build_failure"
    assert records[0].failure_source == "job_metadata"


def test_config_rejects_non_numeric_retry_count(monkeypatch):
    monkeypatch.setenv("GITHUB_MAX_RETRIES", "many")

    with pytest.raises(ValueError, match="GITHUB_MAX_RETRIES must be a non-negative integer"):
        AppConfig.from_env()


@pytest.mark.parametrize("repo", ["owner", "/repo", "owner/", "owner/repo/extra"])
def test_split_repo_rejects_invalid_values(repo):
    with pytest.raises(ValueError, match="owner/name"):
        GitHubClient._split_repo(repo)


def cutoff() -> datetime:
    return datetime(2026, 7, 1, tzinfo=UTC)


def test_request_retries_transient_server_error():
    session = FakeSession([FakeResponse({}, status_code=503), FakeResponse([])])
    client = GitHubClient(
        AppConfig(github_max_retries=1, github_retry_backoff_seconds=0), session=session
    )

    assert client.fetch_pull_requests("owner/repo", cutoff(), limit=1) == []
    assert len(session.calls) == 2


def test_request_does_not_retry_not_found():
    session = FakeSession([FakeResponse({}, status_code=404)])
    client = GitHubClient(AppConfig(github_max_retries=2), session=session)

    with pytest.raises(Exception, match="not found"):
        client.fetch_pull_requests("owner/repo", cutoff(), limit=1)
    assert len(session.calls) == 1


def test_rate_limit_error_includes_reset_time():
    response = FakeResponse(
        {"message": "API rate limit exceeded"},
        status_code=403,
        headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1784563200"},
    )
    with pytest.raises(Exception, match="Rate limit"):
        GitHubClient(
            AppConfig(github_max_retries=0), session=FakeSession([response])
        ).fetch_pull_requests("owner/repo", cutoff(), limit=1)


def test_authentication_error_mentions_github_token():
    response = FakeResponse({"message": "Bad credentials"}, status_code=401)
    with pytest.raises(Exception, match="GITHUB_TOKEN"):
        GitHubClient(AppConfig(), session=FakeSession([response])).fetch_pull_requests(
            "owner/repo", cutoff(), limit=1
        )
