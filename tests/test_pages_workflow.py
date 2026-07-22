from pathlib import Path

WORKFLOW_PATH = Path(".github/workflows/pages.yml")


def test_pages_workflow_builds_and_deploys_demo() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    expected_fragments = [
        "push:",
        "branches: [main]",
        "workflow_dispatch:",
        "actions/configure-pages@v5",
        "name: github-pages",
        "url: ${{ steps.deployment.outputs.page_url }}",
        "group: pages",
        "cancel-in-progress: true",
        "pages: write",
        "id-token: write",
        'python-version: "3.11"',
        "python -m pip install -r requirements.txt",
        "python -m app.main --demo --output-dir site --snapshot-dir site/snapshots",
        "actions/upload-pages-artifact@v4",
        "path: site",
        "actions/deploy-pages@v4",
    ]
    for fragment in expected_fragments:
        assert fragment in workflow

    configure_index = workflow.index("actions/configure-pages@v5")
    upload_index = workflow.index("actions/upload-pages-artifact@v4")
    deploy_index = workflow.index("actions/deploy-pages@v4")
    assert configure_index < upload_index < deploy_index
