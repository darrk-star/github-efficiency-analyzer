# Failure Trends v2 Design

## Objective

Extend the portfolio CLI with explainable repeated-failure analysis. The v2 feature turns individual failed workflow runs into stable failure fingerprints, stores compact JSON snapshots, compares adjacent analysis windows, and identifies new, persistent, resolved, regressed, and potentially flaky CI issues.

This remains a CLI-first portfolio feature. It demonstrates deterministic text normalization, domain modeling, local persistence, temporal comparison, and testable reporting without introducing a web application or external data service.

## Success Criteria

- Equivalent failure messages with timestamps, paths, line numbers, UUIDs, or numeric run identifiers produce the same fingerprint.
- Distinct failure causes do not collapse into the same fingerprint merely because they share a category.
- A snapshot can be written and read as stable JSON without storing full logs.
- Comparing two snapshots correctly identifies `new`, `persistent`, `resolved`, and `regressed` issues.
- Alternating success/failure observations for the same issue can be marked `suspected_flaky`; consecutive failures are not.
- The weekly digest reports the top three actionable recurring issues and clearly reports when no baseline snapshot exists.
- Existing v1 metrics and all v1 tests remain unchanged and passing.
- README includes a local, reproducible two-snapshot demo and honest limitations.

## Scope

### Included

- Deterministic failure-log normalization and fingerprint generation.
- Compact JSON snapshots under a configurable snapshot directory.
- Current-versus-previous snapshot comparison.
- Issue lifecycle status and suspected-flaky detection.
- CLI option for snapshot output and baseline lookup.
- Weekly Markdown digest sections for recurring issues and trend status.
- Unit tests for normalization, persistence, comparison, flaky logic, and CLI behavior.

### Excluded

- SQLite or another database.
- Web UI or dashboard.
- LLM, embeddings, or probabilistic clustering.
- Full-log persistence.
- Multi-repository or organization-level aggregation.
- Slack, Feishu, or other notifications.

## Data Flow

```text
WorkflowRunRecord failures
  -> normalized evidence
  -> stable fingerprint
  -> current snapshot JSON
  -> previous snapshot lookup
  -> lifecycle comparison and flaky signal
  -> weekly digest and top-three actions
```

## Domain Design

### Failure Fingerprints

`app/failure_fingerprint.py` exposes pure functions:

- `normalize_failure_detail(detail: str) -> str`: lowercase and whitespace-normalize evidence, replace volatile tokens with stable placeholders, and preserve meaningful error text.
- `build_failure_fingerprint(category: str, detail: str) -> str`: hash the category plus normalized evidence with SHA-256 and return a short stable identifier.

Normalization removes only known noise:

- ISO timestamps and common date/time forms.
- Windows and Unix absolute path prefixes while retaining the basename/context.
- Line-number suffixes such as `:42`.
- UUIDs and long hexadecimal IDs.
- Standalone numeric run/build identifiers.

The category remains part of the fingerprint input, but category alone never identifies an issue. If detail is missing, use a stable `unknown` token rather than an empty hash input.

### Snapshot Schema

`app/snapshots.py` writes one JSON document per analysis window:

```json
{
  "schema_version": 1,
  "repo": "owner/name",
  "window_days": 14,
  "generated_at": "2026-07-20T12:00:00+00:00",
  "total_runs": 20,
  "failed_runs": 6,
  "issues": [
    {
      "fingerprint": "ci-failure-a1b2c3d4",
      "category": "test_failure",
      "normalized_detail": "pytest failed in tests/test_api.py:{line}",
      "example_detail": "pytest failed in tests/test_api.py:42",
      "count": 4,
      "workflows": ["CI"],
      "first_seen": "2026-07-18T00:00:00+00:00",
      "last_seen": "2026-07-20T00:00:00+00:00"
    }
  ]
}
```

The snapshot also stores compact workflow observations:

```json
{
  "observed_at": "2026-07-20T00:00:00+00:00",
  "workflow": "CI",
  "outcome": "failed",
  "fingerprint": "ci-failure-a1b2c3d4"
}
```

Successful observations use `"fingerprint": null`. Snapshot files use a deterministic filename derived from repository and window end date, with the previous snapshot resolved from the immediately preceding equal-length window. The exact filename helper is pure and tested. Full logs and tokens are never written.

### Trend Status

`app/trends.py` compares issue fingerprints:

- `new`: current issue absent from the previous snapshot.
- `persistent`: present in both snapshots with no material increase in count.
- `regressed`: present in both snapshots and current count is greater than previous count.
- `resolved`: present in previous snapshot but absent from current snapshot.

The comparison returns current issues plus resolved issues so the report can show both active and recovered problems. Counts, workflow sets, and dates remain snapshot-derived; no live API calls occur during comparison.

### Suspected Flaky Detection

The v2 snapshot stores a compact workflow observation list containing only run date, workflow name, successful/failed outcome, and the failure fingerprint when one exists. An issue is `suspected_flaky` when the combined previous/current observation sequence contains this pattern on the same workflow:

```text
failure with fingerprint X -> success -> failure with fingerprint X
```

Consecutive failures, a failure followed by success with no recurrence, different fingerprints around the success, and a single observation are not flaky. The comparison reports the number of matching fail-success-fail recurrences.

This is a heuristic signal, not a claim of statistical proof. The report labels it `suspected_flaky` and includes the observed transition count.

## Integration

- `app/metrics.py` builds issue aggregates from failed `WorkflowRunRecord` objects without changing existing summary semantics.
- `app/main.py` accepts `--snapshot-dir` (default `outputs/snapshots`), writes the current snapshot, looks up the previous equal-window snapshot, and passes comparison results to report rendering.
- `app/report.py` adds `## Recurring CI Issues` and `## Trend Status` sections. With no baseline it prints `Baseline unavailable` and still lists current issues.
- Existing CSV and chart outputs remain compatible.

The snapshot directory is created only when the analysis succeeds. Snapshot write failures are operational errors and return a non-zero CLI code rather than silently omitting persistence.

## Testing Strategy

All new production behavior follows TDD:

- Normalization tests prove volatile-token stability and meaningful-text preservation.
- Fingerprint tests prove deterministic output and category/detail separation.
- Snapshot tests prove JSON round-trip, schema version, deterministic filenames, and no full-log fields.
- Trend tests cover all four lifecycle states, count regression, missing baseline, and resolved issues.
- Flaky tests cover alternating outcomes, consecutive failures, and insufficient observations.
- Metrics tests prove existing v1 summaries are unchanged while issue aggregation is added.
- CLI tests prove snapshot directory handling and baseline-unavailable output.

The suite remains network-free. Fake records and local JSON files are sufficient for all v2 tests.

## Portfolio Presentation

README will add:

- The v2 problem statement: pass-rate counts do not explain repeated incidents.
- A two-window local demo using committed sample JSON fixtures or generated test data.
- The issue lifecycle vocabulary and suspected-flaky limitation.
- An interview narrative focused on deterministic normalization, snapshot schema, and pure temporal comparison.
- Explicit limitations: heuristic noise removal, JSON persistence, single repository, and no statistical flakiness confidence.

No claim of production-scale clustering accuracy or predictive reliability will be made.

## Delivery Order

1. Add failing fingerprint normalization and hash tests, then implement pure functions.
2. Add failing snapshot schema/round-trip tests, then implement JSON persistence.
3. Add failing trend lifecycle/flaky tests, then implement comparison.
4. Integrate issue aggregation into metrics and reports without changing v1 semantics.
5. Add CLI snapshot options and baseline-unavailable behavior.
6. Update README with the reproducible v2 demo and limitations.
7. Run the full v1+v2 suite, compile checks, CLI checks, and diff review.

## Definition of Done

- All v1 and v2 tests pass.
- Fingerprints, snapshots, trend statuses, and flaky signals are covered by deterministic tests.
- CLI can write a current snapshot and compare an adjacent local baseline.
- Reports show top recurring issues and do not fabricate a baseline.
- README accurately documents the v2 demo and limitations.
- No SQLite, web UI, notification, or LLM code is introduced.
