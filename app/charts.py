from __future__ import annotations

from pathlib import Path


def write_failure_trend_chart(trend_frame, output_path: Path) -> bool:
    if not trend_frame:
        return False

    try:
        import matplotlib.pyplot as plt
        import pandas as pd
    except ModuleNotFoundError:
        return False

    pivot = (
        pd.DataFrame(trend_frame)
        .pivot(index="date", columns="failure_category", values="count")
        .fillna(0)
    )
    pivot.index = pd.to_datetime(pivot.index)
    pivot = pivot.sort_index()

    fig, ax = plt.subplots(figsize=(10, 5))
    for category in pivot.columns:
        ax.plot(
            pivot.index,
            pivot[category],
            marker="o",
            linewidth=2,
            label=category.replace("_", " "),
        )

    ax.set_title("CI Failure Categories by Day")
    ax.set_xlabel("Date")
    ax.set_ylabel("Failed Runs")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return True


def write_failed_workflow_chart(workflow_frame, output_path: Path, top_n: int = 8) -> bool:
    if not workflow_frame:
        return False

    try:
        import matplotlib.pyplot as plt
        import pandas as pd
    except ModuleNotFoundError:
        return False

    frame = pd.DataFrame(workflow_frame).head(top_n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(frame["workflow"], frame["count"], color="#C44E52")
    ax.set_title("Most Unstable Workflows")
    ax.set_xlabel("Failed Runs")
    ax.set_ylabel("Workflow")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return True
