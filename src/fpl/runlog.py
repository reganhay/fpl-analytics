"""Append one summary line per pipeline run to data/run_log.csv."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

FIELDS = ["timestamp", "stage", "rows_written", "status", "detail"]


def log_run(path: Path, stage: str, rows_written: int, status: str, detail: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(FIELDS)
        writer.writerow(
            [
                datetime.now(UTC).isoformat(timespec="seconds"),
                stage,
                rows_written,
                status,
                detail,
            ]
        )
