from app.failure_fingerprint import build_failure_fingerprint, normalize_failure_detail


def test_normalization_replaces_volatile_tokens_but_preserves_error_context():
    first = normalize_failure_detail(
        r"2026-07-20T10:11:12Z ERROR C:\builds\repo\tests\test_api.py:42 request 12345 failed"
    )
    second = normalize_failure_detail(
        "2026-07-21T09:01:03Z ERROR /tmp/work/tests/test_api.py:99 request 67890 failed"
    )

    assert first == second
    assert "error" in first
    assert "failed" in first


def test_missing_detail_uses_stable_unknown_token():
    assert normalize_failure_detail("") == "unknown"
    assert normalize_failure_detail(None) == "unknown"


def test_fingerprint_is_stable_and_category_aware():
    assert build_failure_fingerprint("test_failure", "pytest failed") == build_failure_fingerprint(
        "test_failure", "pytest failed"
    )
    assert build_failure_fingerprint("test_failure", "pytest failed") != build_failure_fingerprint(
        "build_failure", "pytest failed"
    )
