# GitHub Efficiency Analyzer

Practice project for engineering productivity work with Python.

This tool pulls recent GitHub pull request data and GitHub Actions workflow run data,
then writes local reports for analysis and presentation.

Outputs:
- `outputs/pull_requests.csv`: pull request detail rows
- `outputs/workflow_runs.csv`: workflow run detail rows
- `outputs/summary.md`: combined metrics summary
- `outputs/weekly_digest.md`: short weekly-style CI digest
- `outputs/ci_failure_trend.png`: daily CI failure trend chart
- `outputs/unstable_workflows.png`: most unstable workflow chart

Skills exercised:
- external API usage
- data cleaning and metrics design
- CLI tool structure
- CI failure analysis
- local chart/report generation
- unit testing

Project structure:

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
    test_metrics.py
  .env.example
  requirements.txt
  README.md
```

Quick start:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m app.main --repo microsoft/vscode --days 30 --limit 50
```

Notes:
- Set `GITHUB_TOKEN` in `.env` for better API limits.
- CI failure classification uses workflow logs first, then falls back to job/step metadata.
- Charts are generated only when there is enough failed workflow data to plot.

Good next extensions:
- first review response time
- PR and CI metrics grouped by author or team
- richer log pattern coverage
- HTML dashboard
- Google Sheets or Docs weekly export
