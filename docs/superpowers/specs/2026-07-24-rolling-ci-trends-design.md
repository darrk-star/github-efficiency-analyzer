# Rolling CI Trends Design

## Goal

Extend the existing adjacent-window CI failure comparison with an explainable rolling view of the most recent continuous analysis windows. The feature should make trend claims credible in a portfolio review: it must never infer a trend across a missing or incompatible snapshot, and it must describe confidence as data coverage rather than statistical proof.

## Scope

### Included

- A `--trend-windows` CLI option with a default of `4` and an accepted range of `2` through `8`.
- Loading up to the requested number of strictly adjacent snapshots ending with the current analysis window.
- Per-fingerprint count series, direction, historical-window coverage, heuristic confidence, and flaky recurrence signal.
- Compact rolling-trend sections in the weekly Markdown digest and static HTML report.
- Deterministic offline demo data and tests for discovery, calculations, CLI validation, and rendering.
- README documentation explaining the feature, configuration, and limits of the heuristic.

### Excluded

- Changing existing adjacent comparison statuses: `new`, `persistent`, `regressed`, and `resolved` remain unchanged.
- Database storage, cross-repository aggregation, live API reads for historical data, forecasts, or statistical significance claims.
- Filling gaps with non-adjacent snapshots or extrapolating missing counts.

## Snapshot Selection

The current in-memory snapshot is always the newest element. Historical snapshots are resolved by repeatedly subtracting `window_days` from the current end date and using the existing deterministic filename convention.

The loader accepts a historical snapshot only when all of the following are true:

- It exists at the exact expected adjacent path.
- It uses schema version `1`.
- Its repository and `window_days` exactly match the current snapshot.
- It can be decoded successfully.

The loader stops at the first missing, unreadable, or incompatible snapshot. It returns the continuous suffix that is available, ordered oldest to newest. A bad historical file therefore cannot fail the freshly completed analysis or create a false trend; it merely reduces available history.

## Domain Model and Calculations

`app/trends.py` will gain an independent rolling-trend model and pure calculation function. Existing `TrendComparison` and `compare_snapshots` retain their public behavior.

Each rolling issue contains:

- `fingerprint`, `category`, `workflows`, and `example_detail`, sourced from the newest snapshot in which the issue appears.
- `window_counts`, one count per accepted snapshot, ordered oldest to newest. A fingerprint absent from a window contributes `0`.
- `observed_windows`, the number of accepted continuous windows.
- `trend_direction`: `improving`, `stable`, `worsening`, or `insufficient_data`.
- `confidence`: `low`, `medium`, or `high`.
- `suspected_flaky` and `transition_count`, computed across the accepted snapshots with the existing same-workflow fail-success-fail rule.

Direction compares the first and final counts in the series: final lower is `improving`, final higher is `worsening`, and equal is `stable`. With fewer than two accepted windows, the direction is `insufficient_data`.

Confidence describes continuous historical coverage only:

- `low`: one accepted window.
- `medium`: two or three accepted windows.
- `high`: four or more accepted windows.

It is intentionally not a probability or statistical confidence interval. The report and README will use the label “data coverage confidence” to prevent overclaiming.

## Integration and Reporting

`app/main.py` validates `--trend-windows`, builds the current snapshot, reads the continuous history before writing that snapshot, then passes the ordered snapshots to the rolling calculation. The current snapshot is still written whether historical data is available or not.

Markdown and HTML add a `Rolling CI Trends` section. It shows at most five issues, with worsening issues first, followed by stable and improving issues. Within each direction, more recent failures sort first, then fingerprint. Each row shows the fingerprint, compact `oldest -> newest` count series, direction, data coverage confidence, and flaky marker when applicable.

When only one current snapshot exists, the section explicitly says that rolling history is still being collected instead of implying a trend. The adjacent-window weekly digest section continues to render independently.

The offline demo creates four compatible adjacent snapshots so its committed report demonstrates a high-coverage improving, worsening, and flaky example without network access.

## Testing Strategy

All feature behavior is implemented test-first:

- Snapshot tests cover exact adjacent lookup, oldest-to-newest ordering, stopping at a missing file, and stopping at schema/repository/window incompatibility or malformed JSON.
- Trend tests cover zero-filled count series, all direction values, each confidence level, newest available issue metadata, deterministic ordering, and multi-window flaky recurrences.
- CLI tests cover default value, accepted boundaries, rejected values, wiring of rolling history, and non-fatal history gaps.
- Markdown, HTML, demo, and README tests or deterministic assertions cover normal rows and the history-collection empty state.

The complete test suite remains network-free. Full validation includes pytest, Ruff lint and format checks, mypy, `compileall`, offline demo generation, and `git diff --check`.

## Portfolio Positioning

The README will frame this as a deterministic local time-series analysis layer over compact snapshots. It demonstrates defensive persistence, explicit data-quality boundaries, pure aggregation, and clear communication of uncertainty. Documentation will state that historical windows must be collected by repeat analyses and that confidence measures only continuous data coverage.

## Definition of Done

- Users can request two through eight rolling windows, with four as the default.
- Trends use only a continuous chain of compatible adjacent snapshots and never bridge gaps.
- Existing two-window comparison and all prior output contracts remain compatible.
- Reports make direction and data-coverage confidence understandable and show a truthful no-history state.
- Demo, README, and deterministic tests support the portfolio narrative.
- No live historical API requests, database, forecast, or statistical-confidence claim is introduced.
