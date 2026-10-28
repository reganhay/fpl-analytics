"""The `fpl` command-line tool. Each stage logs a summary line to the run log."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from fpl.client import FPLClient
from fpl.config import Settings, load_settings
from fpl.extract import backfill, extract_daily
from fpl.load import load
from fpl.runlog import log_run


class StageResult(Protocol):
    @property
    def rows_written(self) -> int: ...

    notes: list[str]


def make_client(settings: Settings) -> FPLClient:
    return FPLClient(
        base_url=settings.base_url,
        user_agent=settings.user_agent,
        delay=settings.request_delay,
        timeout=settings.timeout,
        max_attempts=settings.max_attempts,
    )


def run_stage(settings: Settings, stage: str, fn: Callable[[], StageResult]) -> int:
    try:
        result = fn()
    except Exception as exc:
        log_run(settings.run_log, stage, 0, "failed", f"{type(exc).__name__}: {exc}")
        print(f"{stage} failed: {exc}", file=sys.stderr)
        return 1

    detail = "; ".join(result.notes)
    log_run(settings.run_log, stage, result.rows_written, "success", detail)
    print(f"{stage}: wrote {result.rows_written} rows")
    for note in result.notes:
        print(f"  note: {note}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fpl", description="FPL analytics pipeline")
    parser.add_argument(
        "--config", type=Path, default=Path("config.toml"), help="path to config.toml"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    extract = sub.add_parser("extract", help="pull raw data from the FPL API")
    extract_sub = extract.add_subparsers(dest="mode", required=True)
    extract_sub.add_parser("daily", help="daily snapshot plus any newly final gameweeks")

    sub.add_parser("backfill", help="one-off pull of every player's match history")
    sub.add_parser("load", help="load every raw file into the DuckDB raw tables")

    args = parser.parse_args(argv)
    settings = load_settings(args.config)

    if args.command == "extract":
        return run_stage(
            settings, "extract_daily", lambda: extract_daily(make_client(settings), settings)
        )
    if args.command == "backfill":
        return run_stage(settings, "backfill", lambda: backfill(make_client(settings), settings))
    if args.command == "load":
        return run_stage(settings, "load", lambda: load(settings))
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
