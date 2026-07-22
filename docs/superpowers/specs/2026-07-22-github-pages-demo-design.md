# GitHub Pages Demo Design

## Goal

Publish the project's offline portfolio report as a public, zero-configuration GitHub Pages site so a reviewer can open the result without cloning the repository or installing Python.

## Scope

- Add a GitHub Actions workflow dedicated to Pages deployment.
- Trigger deployment after pushes to `main`, with an optional manual `workflow_dispatch` trigger.
- Generate the existing offline demo into a temporary artifact directory during CI.
- Publish the generated `index.html`, charts, CSV files, Markdown files, and snapshots from that directory.
- Keep the existing quality CI workflow unchanged.
- Do not commit generated output files and do not require a GitHub API token.

## Architecture and Data Flow

1. GitHub Actions checks out `main`.
2. The workflow installs the runtime dependencies from `requirements.txt`.
3. The workflow runs `python -m app.main --demo --output-dir site --snapshot-dir site/snapshots`.
4. The Pages upload action packages `site/` as the deployment artifact.
5. The Pages deploy action publishes that artifact to the repository's GitHub Pages environment.

The report generator remains the single source of truth. The workflow only provides a reproducible build-and-publish wrapper around the existing demo command.

## Workflow and Permissions

- Use the official Pages actions: configure-pages, upload-pages-artifact, and deploy-pages.
- Grant only `contents: read`, `pages: write`, and `id-token: write` permissions.
- Set `concurrency` so a newer `main` deployment cancels an older pending deployment.
- Use the repository's existing Python 3.11-compatible dependency constraints.

## Failure Handling

- If dependency installation or demo generation fails, the workflow stops before publishing.
- No partial site is deployed.
- The existing quality workflow remains the place for lint, type, and test failures.

## Verification

- Run the demo command locally and confirm `site/index.html` is generated.
- Run the existing test suite.
- Run Ruff and mypy locally when dependencies are available.
- Validate the workflow YAML structure and inspect the generated artifact paths.

## Acceptance Criteria

- A push to `main` starts the Pages deployment workflow.
- The workflow generates and publishes a self-contained static report.
- The public site opens at the repository's GitHub Pages URL and displays the existing portfolio report.
- Existing CI checks continue to run independently and remain unchanged.
