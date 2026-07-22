# Portfolio README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the README immediately communicate the project's online result, fast demo path, and strongest engineering capabilities.

**Architecture:** Keep the existing technical README intact and prepend a focused portfolio hero. The hero links to the deployed Pages site and offline demo, uses an existing repository-local chart as the preview image, and states only capabilities already implemented and tested.

**Tech Stack:** Markdown, GitHub Pages, PowerShell, pytest

---

## File Structure

- Modify `README.md` at the top: add portfolio links, preview image, and capability bullets before `Why This Project`.
- Create no new runtime code or generated output.

### Task 1: Add the Portfolio Hero

**Files:**
- Modify: `README.md:1-7`
- Verify: `assets/ci_failure_trend.png`

- [ ] **Step 1: Replace the opening introduction with the approved hero**

Use this exact Markdown before the existing `## Why This Project` section:

```markdown
# GitHub Efficiency Analyzer

> Turn GitHub pull request and Actions data into explainable engineering-efficiency insights.

[Live report](https://darrk-star.github.io/github-efficiency-analyzer/) · [Offline demo](#offline-portfolio-demo) · [Run tests](#verification)

![Portfolio report preview](assets/ci_failure_trend.png)

## What This Demonstrates

- Resilient GitHub REST API integration with pagination, bounded retries, rate-limit handling, and typed payload translation.
- Explainable CI diagnosis using deterministic classification, evidence extraction, and stable failure fingerprints.
- Snapshot-based trend comparison that identifies `new`, `persistent`, `regressed`, `resolved`, and `suspected_flaky` issues.
- Reproducible CSV, Markdown, PNG, JSON, and static HTML reporting with automated tests and GitHub Pages deployment.

This is a focused portfolio project for Python backend and engineering productivity roles. It is designed to be easy to run, inspect, test, and discuss in an interview.
```

Remove the old duplicate two-sentence introduction, but keep the existing `## Why This Project` heading and everything below it unchanged.

- [ ] **Step 2: Verify the hero references real repository content**

Run:

```powershell
Test-Path assets/ci_failure_trend.png
Select-String -Path README.md -Pattern "https://darrk-star.github.io/github-efficiency-analyzer/", "Offline demo", "What This Demonstrates"
```

Expected: `True`, one live URL, one offline demo link, and one capability heading.

- [ ] **Step 3: Inspect Markdown structure and diff**

Run: `Get-Content README.md -TotalCount 45; git diff -- README.md; git diff --check`

Expected: the hero appears before `## Why This Project`, the existing technical sections remain present, and no whitespace errors are reported.

- [ ] **Step 4: Commit the README change**

```powershell
git add README.md
git commit -m "docs: make readme portfolio ready"
```

### Task 2: Run Final Verification

**Files:**
- Verify: `README.md`
- Verify: `assets/ci_failure_trend.png`

- [ ] **Step 1: Run the complete existing test suite**

Run: `python -m pytest -q`

Expected: `64 passed`.

- [ ] **Step 2: Confirm no generated or unrelated files changed**

Run: `git status --short --branch`

Expected: only the intended README commit is present, with no changes under `outputs/` or `.storage/`.

- [ ] **Step 3: Push the branch and create a PR**

Run: `git push -u origin codex/portfolio-readme`

Expected: remote branch created. Open a PR into `main` titled `[codex] make README portfolio ready`.

- [ ] **Step 4: Verify the rendered README after merge**

Open the repository Code page and confirm the live report link, preview image, capability bullets, and existing technical sections render correctly.
