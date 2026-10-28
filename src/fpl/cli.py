"""The `fpl` command-line tool. Each stage logs a summary line to the run log."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from fpl.client import FPLClient
from fpl.config import Settings, load_settings
from fpl.extract import ExtractResult, backfill, extract_daily
from fpl.runlog import log_run


def make_client(settings: Settings) -> FPLClient:
    return FPLClient(
        base_url=settings.base_url,
        user_agent=settings.user_agent,
        delay=settings.request_delay,
        timeout=settings.timeout,
        max_attempts=settings.max_attempts,
    )


def run_stage(
    settings: Settings, stage: str, fn: Callable[[FPLClient, Settings], ExtractResult]
) -> int:
    try:
        result = fn(make_client(settings), settings)
    except Exception as exc:
        log_run(settings.run_log, stage, 0, "failed", f"{type(exc).__name__}: {exc}")
        print(f"{stage} failed: {exc}", file=sys.stderr)
        return 1

    detail = "; ".join(result.notes)
    log_run(settings.run_log, stage, len(result.files_written), "success", detail)
    print(f"{stage}: wrote {len(result.files_written)} files")
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

    args = parser.parse_args(argv)
    settings = load_settings(args.config)

    if args.command == "extract":
        return run_stage(settings, "extract_daily", extract_daily)
    if args.command == "backfill":
        return run_stage(settings, "backfill", backfill)
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
