# README Report Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the README's sparse CI chart preview with a clean first-screen capture of the deployed HTML report.

**Architecture:** Use the deployed static report as the visual source of truth, capture only the report viewport without browser or desktop chrome, save one repository-local PNG, and update the existing README image reference. No application code, generated output, or Pages workflow changes are needed.

**Tech Stack:** GitHub Pages, browser capture, PNG, Markdown, pytest

---

## File Structure

- Create `assets/portfolio-report-preview.png`: clean report screenshot for the README hero.
- Modify `README.md:5`: replace the current `assets/ci_failure_trend.png` hero image reference.
- Create no runtime code and modify no existing chart asset.

### Task 1: Capture and Add the Report Preview

**Files:**
- Create: `assets/portfolio-report-preview.png`
- Modify: `README.md:5`

- [ ] **Step 1: Capture the deployed report viewport**

Open `https://darrk-star.github.io/github-efficiency-analyzer/` in a clean browser viewport around 1440 pixels wide. Capture from the report page's top edge through the first row of `Pull Request Metrics` cards. Exclude browser chrome, scrollbars, desktop watermarks, and unrelated UI. Save the PNG as:

```text
assets/portfolio-report-preview.png
```

- [ ] **Step 2: Inspect the image dimensions and visual content**

Run:

```powershell
python -c "from PIL import Image; image=Image.open('assets/portfolio-report-preview.png'); print(image.size, image.mode)"
```

Expected: a wide RGB/RGBA PNG with readable report title and first metric cards, not a screenshot of browser chrome.

- [ ] **Step 3: Replace the README hero image reference**

Change only this line:

```markdown
![Portfolio report preview](assets/ci_failure_trend.png)
```

to:

```markdown
![Portfolio report preview](assets/portfolio-report-preview.png)
```

- [ ] **Step 4: Verify image references and repository assets**

Run:

```powershell
Test-Path assets/portfolio-report-preview.png
(Select-String -Path README.md -Pattern 'assets/portfolio-report-preview.png').Count
Test-Path assets/ci_failure_trend.png
```

Expected: `True`, `1`, `True`.

- [ ] **Step 5: Commit the visual change**

```powershell
git add README.md assets/portfolio-report-preview.png
git commit -m "docs: add polished report preview"
```

### Task 2: Run Final Verification

**Files:**
- Verify: `README.md`
- Verify: `assets/portfolio-report-preview.png`

- [ ] **Step 1: Run the complete test suite and diff checks**

Run:

```powershell
python -m pytest -q
git diff --check
```

Expected: `64 passed` and no whitespace errors.

- [ ] **Step 2: Inspect the final README hero**

Run: `Get-Content README.md -TotalCount 20; git status --short --branch`

Expected: the README references the new preview, the old chart asset remains present, and only the intended visual files are changed.

- [ ] **Step 3: Push the branch and create a PR**

Run: `git push -u origin codex/portfolio-visual`

Expected: remote branch created. Open a PR into `main` titled `[codex] add polished README report preview`.

- [ ] **Step 4: Verify the rendered README after merge**

Open the repository Code page and confirm the new screenshot is legible at README width and contains no browser or desktop chrome.
