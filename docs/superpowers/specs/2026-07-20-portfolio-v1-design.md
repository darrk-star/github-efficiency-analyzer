# Portfolio v1 Reliability Upgrade

## Objective

Turn GitHub Efficiency Analyzer into a credible portfolio project for Python backend and engineering productivity roles. The v1 should demonstrate reliable API integration, explicit metric definitions, testable business logic, useful error handling, and explainable CI failure diagnosis.

The goal is not to build a production SaaS platform. The goal is a focused command-line application whose behavior and engineering decisions are easy to verify and discuss in an interview.

## Success Criteria

- All automated tests pass and cover the highest-risk data collection and metric behaviors.
- Pull request and workflow collection do not silently omit records because of incorrect pagination or time-window assumptions.
- CI outcomes have documented, consistent semantics across summaries, trends, charts, and reports.
- GitHub API failures produce concise, actionable CLI errors and a non-zero exit status.
- Transient API failures are retried without retrying permanent client errors.
- The repository runs formatting/lint, type checking, and tests in GitHub Actions.
- The README accurately explains the architecture, metric definitions, engineering decisions, limitations, and a reproducible demo.

## Scope

### Included

- Correct pull request and workflow pagination and filtering.
- Explicit workflow outcome aggregation.
- GitHub client retry, timeout, rate-limit, and error handling.
- CLI argument validation and reliable output formatting.
- Explainable rule-based CI failure classification.
- Unit and integration-style tests using injected or mocked HTTP sessions.
- Ruff, mypy, pytest, and GitHub Actions configuration.
- Portfolio-oriented README improvements.

### Excluded

- Web UI or dashboard.
- Database or historical persistence.
- Organization-wide or multi-repository aggregation.
- Scheduled execution and chat notifications.
- LLM-based failure classification.
- Authentication flows beyond a GitHub personal access token.

## Architecture

The existing module structure remains in place because it is appropriate for the size of the project. The upgrade will improve boundaries without introducing a large service or repository abstraction layer.

- `app/github_client.py` owns HTTP requests, pagination, response validation, retry behavior, and translation from GitHub payloads into domain records.
- `app/models.py` owns immutable records and any small outcome-oriented domain types needed to make metric semantics explicit.
- `app/ci_failure_analysis.py` owns deterministic failure classification and returns both the category and human-readable evidence.
- `app/metrics.py` owns pure aggregation and export-row construction. It must not perform network or filesystem operations except the existing dedicated CSV writer.
- `app/report.py` and `app/charts.py` render already-computed data without redefining failure semantics.
- `app/main.py` validates input, coordinates the workflow, prints results, and converts known operational failures into user-facing messages and exit codes.

Dependency injection will be lightweight: `GitHubClient` will accept an optional requests-compatible session. Production uses a configured session; tests provide a controlled fake or mock session.

## Data Collection

### Pull Requests

GitHub's pull request list endpoint is sorted by `updated_at`, not `created_at`. Therefore the collector must not stop at the first PR whose creation timestamp is outside the selected window.

The collector will page through results up to the configured inspection limit, filter records by `created_at >= created_after`, and hydrate only selected PRs. The limit means the maximum number of matching PRs returned, not merely the number of list entries examined. Pagination stops when there are no more pages or when the matching limit is reached.

This favors correctness over the previous unsafe early exit. The README will state that the selected time window is based on PR creation time.

### Workflow Runs

Workflow runs are returned newest first by creation time, so collection may stop once a page crosses the requested creation-time boundary. Only failed or timed-out runs require log analysis. Successful, neutral, skipped, and cancelled runs will not download logs.

Jobs remain useful for fallback classification and failure details. Job fetching will be limited to runs for which it is needed rather than performed for every successful run.

### API Reliability

The HTTP layer will use bounded retries for transient failures such as connection errors, timeouts, HTTP 429, and selected 5xx responses. Permanent 4xx failures will fail immediately.

Errors will be translated into a project-specific exception carrying an actionable message. Rate-limit responses should mention the reset time when GitHub provides it. Authentication failures should point the user to `GITHUB_TOKEN`; repository and permission failures should identify the affected repository or operation.

## Metric Semantics

Workflow conclusions will be treated as separate outcome groups:

- Successful: `success`.
- Failed: `failure`, `timed_out`, `action_required`, and other explicitly unsuccessful conclusions.
- Cancelled: `cancelled`.
- Excluded from success-rate denominator: `neutral`, `skipped`, `stale`, and missing/incomplete conclusions.

The success rate is:

`successful / (successful + failed) * 100`

Cancelled and excluded runs will be reported separately instead of being silently treated as failures or successes. Failure summaries, daily trends, unstable-workflow rankings, and weekly digests will all use the same failed-outcome predicate.

PR metrics retain their current definitions for v1:

- Merge time is `merged_at - created_at` for merged PRs.
- PR size is additions plus deletions.
- Comment volume is issue comments plus review comments.
- The time window is based on PR creation time.

The README will state these definitions and their limitations. First-review response time and actual reviewer participation remain future work because `requested_reviewers` is not a reliable historical review record.

## Failure Diagnosis

Classification remains deterministic and rule-based. Each result will expose:

- A stable category.
- A concise evidence line or fallback job/step detail.
- A source indicating whether the result came from logs, job metadata, the workflow conclusion, or a fallback.

Rules will prefer specific signatures over generic ones. In particular, a generic `exit code 1` line must not automatically imply a test failure. Unknown failures remain visible as `unknown_failure`; the tool must not claim greater accuracy than the evidence supports.

No statistical or LLM classifier is included in v1. Explainability and predictable behavior are more valuable for this portfolio iteration.

## CLI Behavior

- `--repo` must use non-empty `owner/name` form.
- `--days` and `--limit` must be positive integers.
- Numeric zero values must print as zero, not `N/A`.
- Known GitHub/API/configuration errors must be printed without a Python traceback by default and return a non-zero exit status.
- Generated file paths remain visible after successful execution.
- Debug-level traceback behavior is out of scope unless it can be added without complicating the interface.

## Testing Strategy

Behavior changes will follow test-driven development. Each production change starts with a focused failing test, followed by the minimum implementation needed to pass it.

The test suite will cover:

- Existing PR and workflow aggregation behavior.
- Outcome semantics, including success, failure, cancelled, neutral, skipped, incomplete, and zero-rate cases.
- PR pagination with old-but-recently-updated records mixed with newly created records.
- Workflow time-window pagination.
- Successful runs avoiding unnecessary jobs and log requests.
- Failed-run log classification and metadata fallback.
- Retryable versus non-retryable API responses.
- Rate-limit and authentication error messages.
- Invalid CLI arguments and zero-value rendering.
- CSV/report rendering contracts where regressions would affect the portfolio demo.

HTTP tests will assert observable requests and returned records rather than internal helper call counts where possible.

## Engineering Tooling

- Ruff will provide formatting and lint checks.
- mypy will check the application package with a pragmatic initial configuration.
- pytest remains the test runner.
- A GitHub Actions workflow will install dependencies and run Ruff, mypy, and pytest on a supported Python version matrix kept intentionally small.
- Runtime and development dependencies will be clearly identified. The installation path must remain simple for reviewers.

Tooling configuration may use `pyproject.toml` so lint, format, type, and pytest settings live in one discoverable place.

## Portfolio Presentation

The README will lead with the problem and differentiator rather than a feature inventory. It will include:

- A concise project pitch for Python backend and engineering productivity roles.
- Architecture and data-flow explanation.
- Explicit metric definitions.
- Engineering decisions and trade-offs.
- Test and CI instructions.
- A reproducible demo command and representative output clearly labeled as a sample.
- Current limitations and a short roadmap.
- Existing charts where they support the story.

Claims will be evidence-based. The README will not claim production readiness, classification accuracy, test coverage percentage, or performance improvements unless measured.

## Delivery Order

1. Establish green baseline expectations by fixing stale tests without masking real defects.
2. Define and test shared workflow outcome semantics.
3. Correct pagination and reduce unnecessary API requests.
4. Add retry and actionable error handling.
5. Improve failure classification explainability.
6. Harden CLI validation and output behavior.
7. Add Ruff, mypy, and GitHub Actions.
8. Rewrite README around verified behavior and engineering decisions.
9. Run the full verification suite and inspect the final repository diff.

## Risks and Mitigations

- GitHub API pagination behavior can be difficult to reproduce locally. Mocked multi-page fixtures will make boundary cases deterministic.
- Log archives can be large. v1 reduces downloads to failed runs; streaming and archive-size limits are possible follow-up work.
- Strict type checking may trigger a broad refactor. The initial mypy scope will focus on `app` with practical library settings rather than pursuing strict mode.
- External GitHub behavior can change or be rate-limited. Tests will not depend on live network access; the README demo remains separately reproducible with a token.

## Definition of Done

- The full local test suite passes.
- Ruff formatting and lint checks pass.
- mypy passes for the configured application scope.
- The CLI compiles and its validation/error tests pass.
- GitHub Actions is configured to run the same checks.
- README claims match verified repository behavior.
- No unrelated user files or changes are modified.
