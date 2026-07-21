# Static HTML Report Design

## Goal

Add a single-file static HTML report so the project can present its existing PR metrics, CI summaries, recurring failure analysis, snapshot comparison, and charts in a form that is easier to browse than Markdown but still requires no web server or frontend framework.

## Problem

The project already produces strong textual output and PNG charts, but those outputs are spread across Markdown, CSV, and JSON files. For a portfolio review, that is useful but not ideal: an interviewer has to open multiple artifacts and mentally connect them. A static HTML page would provide one clear entry point that ties the existing outputs together without changing the project's CLI-first identity.

The new report should not replace the existing outputs. Markdown, CSV, PNG, and snapshot JSON remain the primary data artifacts. HTML is a presentation layer for the same analysis results.

## Scope

In scope:

- Generate a static `index.html` report from existing metrics and digest objects.
- Support both live GitHub mode and offline demo mode.
- Reuse the current Markdown/CSV/PNG/snapshot generation pipeline.
- Reference existing chart images rather than re-rendering them in the browser.
- Keep the report self-contained enough to open directly from disk.
- Add tests for HTML content and file creation.
- Update README with the HTML report output and the offline demo story.

Out of scope:

- Web servers, Flask, FastAPI, Streamlit, Next.js, React, Vue, or any client-side app framework.
- Dynamic interactivity beyond basic links and anchor navigation.
- Database-backed or authenticated report storage.
- Replacing the current CLI outputs.
- Real-time refresh, polling, or browser-based filtering.

## User Experience

After running either demo mode or live analysis, the project writes:

- `outputs/index.html`

Opening that file should show:

- repository and window summary
- PR metrics
- CI metrics
- recurring CI issues with `new`, `persistent`, `regressed`, `resolved`, and `suspected_flaky`
- links to the existing Markdown, CSV, and snapshot outputs
- embedded or referenced PNG charts

The page should be readable directly from disk in a browser with no backend process.

## Design Options

Recommended option: one HTML template built with standard library string formatting.

Trade-offs:

- Pros: no new dependencies, small surface area, easy to test, easy to ship.
- Cons: less convenient than a template engine for very large markup.

Alternative: use Jinja2.

Trade-offs:

- Pros: nicer template ergonomics.
- Cons: adds a dependency for a small reporting layer and weakens the project's minimal CLI story.

Alternative: generate HTML from Markdown.

Trade-offs:

- Pros: implementation is short.
- Cons: loses control over layout and metrics presentation, and makes the HTML feel like a conversion artifact rather than a deliberate portfolio page.

Recommended path: standard library HTML generation with small helper functions.

## Architecture

Add one focused module, `app/html_report.py`, that converts already-computed analysis objects into HTML.

The module should take existing domain outputs as inputs and return or write a single HTML document. It should not perform GitHub API calls, snapshot comparisons, or duplicate metric logic. That keeps the report layer thin and deterministic.

Suggested public function:

```python
def write_html_report(
    output_path: Path,
    repo: str,
    days: int,
    pr_summary: PullRequestMetricsSummary,
    workflow_summary: WorkflowMetricsSummary,
    digest: WeeklyCiDigest,
    comparison: TrendComparison,
    artifact_links: dict[str, Path],
) -> None:
    ...
```

The report should:

- escape all dynamic content with `html.escape`
- render a compact summary header
- show metric cards or sections for PR and CI data
- include a recurring issues section with status badges
- list artifact links for Markdown, CSV, snapshots, and charts
- reference chart PNG files with relative paths so the page works when opened locally

If the page includes small inline CSS, keep it contained in the HTML file itself. Do not introduce a stylesheet pipeline or build step.

## Data Flow

The existing analysis flow stays the same:

1. collect or load data
2. compute summaries, weekly digest, and trend comparison
3. write CSV, Markdown, PNG, and snapshot JSON files
4. write `index.html` using the same computed objects

For offline demo mode, the HTML report should use the fixture-backed outputs. For live mode, it should use the GitHub-backed outputs. In both cases, the HTML file points to the artifacts created in the same output directory.

## Error Handling

HTML report generation should be best-effort but not silent about core failures:

- If the analysis already failed, HTML generation should not run.
- If a chart path is missing, the page should show a readable "not generated" state instead of failing.
- If optional artifact links are missing, the page should omit them rather than breaking.

The report layer should not catch unrelated analysis errors. Those remain the responsibility of the existing CLI error handling.

## Testing

Add tests that prove:

- the HTML report file is written
- the page includes the repo name, recurring issue section, and status labels
- the page links to artifact files using the expected filenames
- offline demo mode also writes the HTML report
- the code remains compatible with the current CLI outputs

The tests should assert on the generated HTML text rather than internal implementation details.

## Documentation

README updates:

- add `index.html` to the outputs list
- explain that the HTML page is the best single artifact for a portfolio review
- add a short usage example for opening `outputs/index.html`
- keep the offline demo section and fix any malformed formatting in the existing demo examples

## Success Criteria

- Running the CLI produces `outputs/index.html`.
- The page presents the existing metrics and recurring issue statuses clearly.
- The page can be opened directly from disk.
- Existing Markdown, CSV, PNG, and snapshot outputs remain unchanged.
- Both demo and live modes continue to work.
- Full tests pass.
