# README Report Preview Design

## Goal

Replace the sparse CI trend chart at the top of the README with a polished screenshot of the deployed HTML report so the repository landing page communicates the complete product rather than one isolated chart.

## Selected Direction

Use a clean browser capture of the GitHub Pages report from the top of the page through the first row of pull request metric cards. This framing includes the report title, repository context, explanation, and real metrics while remaining readable inside GitHub's README column.

## Image Strategy

- Capture `https://darrk-star.github.io/github-efficiency-analyzer/` using a desktop viewport around 1440 pixels wide.
- Exclude browser chrome, desktop watermarks, scrollbars, and unrelated operating-system UI.
- Capture the page from the top through the first pull request metric row.
- Save the optimized PNG as `assets/portfolio-report-preview.png`.
- Keep the image wide enough for readable text but compress it to a practical repository size.
- Replace only the README image path; keep the existing alt text and portfolio hero content.

## Alternatives Considered

- **Current CI chart:** small file and technically relevant, but too sparse to represent the full project.
- **Title-only crop:** visually clean, but hides the analyzer's data and makes the project look like a generic landing page.
- **Composite image:** shows more sections, but adds maintenance and makes text too small in the README.

The full first-screen capture provides the best balance of product clarity, visual impact, and maintainability.

## Verification

- Confirm the image contains no browser or desktop chrome.
- Confirm the title and first metric cards are readable at GitHub README width.
- Confirm `assets/portfolio-report-preview.png` exists and is referenced once by `README.md`.
- Confirm the previous chart asset remains available for technical sections and is not deleted.
- Run `python -m pytest -q` and `git diff --check`.

## Acceptance Criteria

- The repository landing page shows a complete report preview instead of an isolated plot.
- The image is clean, legible, repository-local, and free of personal desktop watermarks.
- The live report, offline demo, and testing links remain unchanged.
- No application behavior or generated output directory is modified.
