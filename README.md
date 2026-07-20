# GitHub Efficiency Analyzer

A Python CLI that turns GitHub pull request and Actions data into explainable engineering-efficiency reports. It demonstrates resilient REST API integration, explicit metric semantics, deterministic CI log classification, typed domain models, automated tests, and CI quality checks.

This is a focused portfolio project for Python backend and engineering productivity roles. It is designed to be easy to run, inspect, test, and discuss in an interview.

## Why This Project

Engineering teams often need answers that are more specific than a raw GitHub activity feed:

- How long do pull requests take to merge?
- Which workflows fail repeatedly?
- Are failures caused by tests, builds, dependencies, permissions, or infrastructure?
- Can a weekly report explain what deserves attention next?

The analyzer combines pull request metrics with GitHub Actions stability analysis and produces CSV, Markdown, and chart outputs from one reproducible CLI command.

## Architecture

```text
GitHub REST API
  -> resilient collection and pagination
  -> typed PR/workflow records
  -> pure metrics and deterministic failure classification
  -> CSV, Markdown, and PNG reports
```

| Module | Responsibility |
| --- | --- |
| `app/github_client.py` | GitHub HTTP calls, pagination, retries, rate-limit errors, and payload translation |
| `app/models.py` | Immutable domain records and shared workflow outcome semantics |
| `app/ci_failure_analysis.py` | Explainable rule-based log classification and evidence extraction |
| `app/metrics.py` | Pure PR/CI aggregation, trends, weekly digest, and CSV rows |
| `app/report.py` | Markdown report rendering |
| `app/charts.py` | Optional PNG charts from already-computed rows |
| `app/main.py` | CLI validation, orchestration, output paths, and exit codes |

## Engineering Decisions

### Correct pagination

GitHub pull requests are returned sorted by `updated_at`, while this project defines its reporting window by `created_at`. The collector therefore filters matching PRs without stopping at the first old record. This avoids silently omitting a recently created PR that appears after an old PR updated recently.

Workflow runs are returned newest first by creation time, so workflow collection can stop safely at the first run outside the requested window.

### Fewer expensive requests

Successful, neutral, skipped, and cancelled workflow runs do not need diagnostic logs. Jobs and log archives are fetched only for unsuccessful runs that need classification. This keeps the normal path cheaper and makes the trade-off visible in tests.

### Explicit outcome semantics

Workflow conclusions are grouped consistently across summaries, trends, charts, and weekly digests:

- `success`: successful
- `failure`, `timed_out`, `action_required`, and other unsuccessful conclusions: failed
- `cancelled`: cancelled and reported separately
- `neutral`, `skipped`, `stale`, and missing conclusions: excluded from the success-rate denominator

The success rate is:

```text
successful / (successful + failed) * 100
```

### Explainable failure diagnosis

Failure classification is deterministic and rule-based. Each classification retains a concise evidence line and a source such as `logs`, `job_metadata`, `conclusion`, or `fallback`. A generic `exit code 1` is not treated as a test failure without stronger evidence. Unknown failures remain visible instead of being presented as confidently classified.

## Metrics

### Pull requests

- Total, merged, and open PR counts
- Average and median merge time: `merged_at - created_at`
- Average PR size: additions plus deletions
- Average changed files
- Average comment volume: issue comments plus review comments
- Top authors by PR count

The PR time window is based on PR creation time. Requested reviewers are exported for context, but they are not presented as historical reviewer participation because the GitHub field does not reliably represent completed reviews.

### GitHub Actions

- Total completed runs
- Successful, failed, cancelled, and excluded run counts
- Success rate using only successful and failed runs
- Average workflow duration
- Failure category distribution
- Most frequently failing workflows
- Daily failure trend and weekly digest

## Outputs

The command writes these files under `outputs/` by default:

- `pull_requests.csv`
- `workflow_runs.csv`
- `summary.md`
- `weekly_digest.md`
- `ci_failure_trend.png`
- `unstable_workflows.png`

## Quick Start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Add a GitHub token to `.env`:

```env
GITHUB_TOKEN=ghp_your_token_here
```

Run an analysis:

```powershell
python -m app.main --repo microsoft/vscode --days 14 --limit 20
```

The CLI validates `owner/name`, positive `--days`, and positive `--limit` before making network calls. GitHub authentication, not-found, rate-limit, timeout, and retry exhaustion errors return a non-zero exit code with an actionable message.

## Quality Checks

The same checks run locally and in `.github/workflows/ci.yml`:

```powershell
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy app
```

HTTP tests use deterministic fake sessions and multi-page fixtures. They do not depend on a live GitHub repository or token.

## Sample Output

The repository includes chart assets and a historical sample run against `microsoft/vscode` for demonstration. Sample values are illustrative and are not guaranteed to match current repository activity.

Example command:

```powershell
python -m app.main --repo microsoft/vscode --days 14 --limit 20
```

Example findings from the historical sample:

- 9 PRs inspected
- 1 merged PR
- Average merge time: 9.65 hours
- 17 completed workflow runs
- Workflow success rate: 17.65%
- Dominant failure type: `build_failure`

## Tests and Current Verification

The local application test suite covers metric semantics, pagination, workflow request optimization, failure classification, retries, rate-limit/authentication errors, and CLI validation. The current branch has 38 passing tests and passes Python compilation checks.

Ruff and mypy configuration is committed and runs in GitHub Actions. In the development environment used for this iteration, package installation for those tools was blocked by the machine's pip/index configuration, so their first authoritative run is expected to come from GitHub Actions.

## Limitations and Roadmap

This v1 intentionally does not include a web dashboard, database, scheduled jobs, organization-wide aggregation, or LLM-based classification. It also does not calculate historical first-review response time because that requires review-event history rather than the current requested-reviewers snapshot.

Useful next steps would be:

1. Persist snapshots for week-over-week comparisons.
2. Add failure fingerprints for repeated incidents and likely flaky tests.
3. Add workflow ownership and notification integrations.
4. Add review-event metrics after introducing the required API collection.

## Interview Talking Points

- I found and fixed a pagination correctness issue caused by GitHub sorting PRs by update time while the report window uses creation time.
- I reduced unnecessary GitHub API work by skipping jobs and log downloads for successful runs.
- I made workflow success-rate semantics explicit instead of mixing cancelled and excluded runs into failures.
- I added bounded retries and user-facing rate-limit/authentication errors around the HTTP client.
- I used deterministic HTTP fixtures so correctness tests do not depend on live network state.
- I kept failure diagnosis rule-based and explainable rather than claiming opaque classifier accuracy.

## Project Structure

```text
github-efficiency-analyzer/
  app/
    charts.py
    ci_failure_analysis.py
    config.py
    github_client.py
    main.py
    metrics.py
    models.py
    report.py
  tests/
    test_github_client.py
    test_main.py
    test_metrics.py
  .github/workflows/ci.yml
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  README.md
```
