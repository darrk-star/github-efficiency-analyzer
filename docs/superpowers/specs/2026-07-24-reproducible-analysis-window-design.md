# Reproducible Analysis Window Design

## Goal

Allow a live GitHub analysis to use a fixed UTC end date so the same command can be rerun with the same reporting window, snapshot name, and adjacent-window baseline.

## CLI Contract

The CLI keeps `--days` as the required window length and adds an optional `--end-date` argument in `YYYY-MM-DD` format.

```powershell
python -m app.main --repo microsoft/vscode --days 14 --end-date 2026-07-24
```

`--end-date` represents the exclusive UTC end boundary at midnight. The collection start boundary is `end_date - days`, and records created at or after that start remain in the report. The end date is also the date used for the generated snapshot filename and adjacent snapshot lookup.

When `--end-date` is omitted, the application preserves its current live-mode behavior by using the current UTC date and timestamp. The offline `--demo` path keeps its fixture-defined timestamps and does not use the option.

## Validation

The argument parser accepts only ISO calendar dates in `YYYY-MM-DD` format. It rejects malformed dates and dates after the current UTC date before any GitHub request is made. The error messages identify the invalid value or explain that future reporting windows are unsupported.

## Data Flow

`app.main` resolves one UTC analysis end timestamp before collection. It derives the created-after boundary from that timestamp and passes it to both pull request and workflow collection. The resolved end date is then reused to construct the snapshot and to locate the adjacent equal-window baseline, preventing collection and persistence from drifting onto different dates.

Reports receive the resolved end date as display metadata. The HTML and Markdown outputs show the reporting window end date next to the existing day count so an exported artifact can be interpreted without its command history.

## Compatibility

Existing commands that only supply `--repo`, `--days`, and `--limit` continue to work. Snapshot schema remains version 1 because `generated_at` already stores the effective end timestamp; only the CLI's source of that value becomes controllable.

## Tests

Tests cover successful parsing, malformed and future dates, fixed-window collection boundaries, deterministic snapshot filenames, report display metadata, and confirmation that demo mode retains fixture behavior. Existing no-option tests continue to prove the default current-UTC behavior.
