# GitHub Pages Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically generate the offline portfolio report and publish it as the repository's GitHub Pages site after every push to `main`.

**Architecture:** A dedicated GitHub Actions workflow builds the existing offline demo into `site/`, uploads that directory as a Pages artifact, and deploys it with the official Pages actions. A small contract test validates the workflow's triggers, permissions, build command, artifact path, and deployment action without introducing a YAML dependency.

**Tech Stack:** GitHub Actions, GitHub Pages official actions, Python 3.11, pytest, existing offline demo CLI

---

## File Structure

- Create `.github/workflows/pages.yml`: build and deploy the static demo site.
- Create `tests/test_pages_workflow.py`: enforce the required Pages workflow contract using Python's standard library.

### Task 1: Define the Pages Workflow Contract

**Files:**
- Create: `tests/test_pages_workflow.py`

- [ ] **Step 1: Write the failing workflow contract test**

```python
from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/pages.yml")


def test_pages_workflow_builds_and_deploys_demo() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    expected_fragments = [
        "push:",
        "workflow_dispatch:",
        "pages: write",
        "id-token: write",
        "python-version: \"3.11\"",
        "python -m pip install -r requirements.txt",
        "python -m app.main --demo --output-dir site --snapshot-dir site/snapshots",
        "actions/upload-pages-artifact@v4",
        "path: site",
        "actions/deploy-pages@v4",
    ]

    for fragment in expected_fragments:
        assert fragment in workflow
```

- [ ] **Step 2: Run the test and verify it fails because the workflow is absent**

Run: `python -m pytest tests/test_pages_workflow.py -q`

Expected: FAIL with `FileNotFoundError` for `.github/workflows/pages.yml`.

- [ ] **Step 3: Commit the contract test**

```powershell
git add tests/test_pages_workflow.py
git commit -m "test: define pages deployment workflow contract"
```

### Task 2: Implement the GitHub Pages Workflow

**Files:**
- Create: `.github/workflows/pages.yml`
- Test: `tests/test_pages_workflow.py`

- [ ] **Step 1: Add the minimal Pages workflow**

```yaml
name: Deploy portfolio report to Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.11"
          cache: pip
      - run: python -m pip install -r requirements.txt
      - run: python -m app.main --demo --output-dir site --snapshot-dir site/snapshots
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v4
        with:
          path: site
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Run the contract test and verify it passes**

Run: `python -m pytest tests/test_pages_workflow.py -q`

Expected: `1 passed`.

- [ ] **Step 3: Generate the site locally with the workflow command**

Run: `python -m app.main --demo --output-dir site --snapshot-dir site/snapshots`

Expected: exit code 0 and `site/index.html` exists with the report artifact files.

- [ ] **Step 4: Remove the local verification output**

Run: `Remove-Item -Recurse -Force -LiteralPath site`

Expected: `site/` no longer exists and `git status --short` does not list generated artifacts.

- [ ] **Step 5: Commit the workflow**

```powershell
git add .github/workflows/pages.yml
git commit -m "ci: deploy portfolio report to pages"
```

### Task 3: Verify the Complete Change

**Files:**
- Verify: `.github/workflows/pages.yml`
- Verify: `tests/test_pages_workflow.py`

- [ ] **Step 1: Run the complete quality suite**

Run:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy app
python -m pytest -q
python -m compileall -q app tests
git diff --check
```

Expected: Ruff passes, formatting is clean, mypy reports no issues, 64 tests pass, compilation succeeds, and `git diff --check` reports no whitespace errors.

- [ ] **Step 2: Inspect final branch state**

Run: `git status --short --branch`

Expected: branch `codex/portfolio-pages` with a clean working tree.

- [ ] **Step 3: Push the branch and create a pull request**

Run: `git push -u origin codex/portfolio-pages`

Expected: the remote branch is created. Create a PR into `main` titled `[codex] publish portfolio report with GitHub Pages`, including the workflow behavior and verification results.

- [ ] **Step 4: Enable GitHub Pages Actions source if GitHub requests it**

Open repository `Settings > Pages`. Under `Build and deployment`, select `GitHub Actions` only if the first deployment reports that Pages is not enabled. Re-run the workflow after saving.

- [ ] **Step 5: Verify the public result after merge**

Open `https://darrk-star.github.io/github-efficiency-analyzer/`.

Expected: the offline portfolio report loads, and artifact links remain within the published site.
