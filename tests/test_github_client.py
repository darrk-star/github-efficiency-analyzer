from __future__ import annotations

from collections import deque
from datetime import datetime, timezone

import pytest

from app.config import AppConfig
from app.github_client import GitHubClient


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None, content=b""):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content

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
        datetime(2026, 7, 1, tzinfo=timezone.utc),
        limit=2,
    )

    assert [record.number for record in records] == [2, 3]


@pytest.mark.parametrize("repo", ["owner", "/repo", "owner/", "owner/repo/extra"])
def test_split_repo_rejects_invalid_values(repo):
    with pytest.raises(ValueError, match="owner/name"):
        GitHubClient._split_repo(repo)
