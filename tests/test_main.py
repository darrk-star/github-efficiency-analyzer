from __future__ import annotations

import argparse

import pytest

from app.github_client import GitHubApiError
from app.main import format_optional_number, positive_int, repo_name, run


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_positive_int_rejects_invalid_values(value):
    with pytest.raises(argparse.ArgumentTypeError, match="positive integer"):
        positive_int(value)


def test_positive_int_accepts_positive_values():
    assert positive_int("7") == 7


@pytest.mark.parametrize("value", ["owner", "/repo", "owner/", "owner/repo/extra"])
def test_repo_name_rejects_invalid_values(value):
    with pytest.raises(argparse.ArgumentTypeError, match="owner/name"):
        repo_name(value)


def test_format_optional_number_preserves_zero():
    assert format_optional_number(0.0) == "0.0"
    assert format_optional_number(None) == "N/A"


def test_run_returns_nonzero_for_github_error(monkeypatch, capsys):
    def raise_api_error(*args, **kwargs):
        raise GitHubApiError("GitHub API unavailable")

    monkeypatch.setattr("app.main.GitHubClient.fetch_pull_requests", raise_api_error)

    assert run(["--repo", "owner/repo"]) == 1
    assert "GitHub API unavailable" in capsys.readouterr().err
