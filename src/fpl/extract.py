"""Pull raw responses from the FPL API and save them untouched as gzipped JSON.

Layout under the raw folder (one folder per endpoint, one file or folder per snapshot date):

    bootstrap_static/2026-10-28.json.gz
    fixtures/2026-10-28.json.gz
    event_status/2026-10-28.json.gz
    entry_history/2026-10-28.json.gz
    entry_transfers/2026-10-28.json.gz
    event_live/2026-10-28/gw07.json.gz
    entry_picks/2026-10-28/gw07.json.gz
    element_summary/2026-10-28/123.json.gz

Every write overwrites the file for the same date, so re-running on the same day never
duplicates data.
"""

from __future__ import annotations

import gzip
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Protocol

import requests

from fpl.config import Settings


class Client(Protocol):
    def get(self, path: str) -> Any: ...


@dataclass
class ExtractResult:
    files_written: list[Path] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def rows_written(self) -> int:
        return len(self.files_written)


def today_utc() -> date:
    # UTC rather than UK time: Windows Python ships without a time-zone database, and a
    # 06:00 UK run falls on the same calendar date in UTC all year round.
    return datetime.now(UTC).date()


def gw_key(gameweek: int) -> str:
    return f"gw{gameweek:02d}"


def raw_path(raw_dir: Path, endpoint: str, snapshot_date: date, key: str | None = None) -> Path:
    if key is None:
        return raw_dir / endpoint / f"{snapshot_date.isoformat()}.json.gz"
    return raw_dir / endpoint / snapshot_date.isoformat() / f"{key}.json.gz"


def write_raw(path: Path, data: Any) -> Path:
    """Write JSON gzipped, via a temporary file so an interrupted run never leaves half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)
    return path


def read_raw(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def already_saved(raw_dir: Path, endpoint: str, key: str) -> bool:
    """True if a keyed file (e.g. one gameweek's live data) exists under any snapshot date."""
    return any((raw_dir / endpoint).glob(f"*/{key}.json.gz"))


def latest_raw(raw_dir: Path, endpoint: str) -> Any | None:
    """Load the most recent dated file for an un-keyed endpoint, or None if there isn't one."""
    files = sorted((raw_dir / endpoint).glob("*.json.gz"))
    return read_raw(files[-1]) if files else None


def final_gameweeks(bootstrap: dict[str, Any], event_status: dict[str, Any]) -> list[int]:
    """Gameweeks whose points are final and safe to store.

    A gameweek counts as final when bootstrap-static marks it finished and data-checked.
    event-status describes the most recent gameweek; if it says bonus points are not all
    added or leagues are not yet updated, that gameweek is held back until a later run.
    """
    final = {
        e["id"] for e in bootstrap.get("events", []) if e.get("finished") and e.get("data_checked")
    }
    statuses = event_status.get("status", [])
    if statuses:
        current = statuses[0]["event"]
        settled = all(s.get("bonus_added") for s in statuses) and event_status.get("leagues") == (
            "Updated"
        )
        if not settled:
            final.discard(current)
    return sorted(final)


def played_gameweeks(history: dict[str, Any] | None) -> set[int]:
    """Gameweeks the manager had a team in, from entry/{id}/history."""
    if not history:
        return set()
    return {row["event"] for row in history.get("current", [])}


def extract_daily(
    client: Client, settings: Settings, snapshot_date: date | None = None
) -> ExtractResult:
    """The daily pull: core snapshots, plus any finished gameweek data not yet saved."""
    snapshot_date = snapshot_date or today_utc()
    raw = settings.raw_dir
    result = ExtractResult()

    bootstrap = client.get("bootstrap-static/")
    result.files_written.append(
        write_raw(raw_path(raw, "bootstrap_static", snapshot_date), bootstrap)
    )
    result.files_written.append(
        write_raw(raw_path(raw, "fixtures", snapshot_date), client.get("fixtures/"))
    )
    event_status = client.get("event-status/")
    result.files_written.append(
        write_raw(raw_path(raw, "event_status", snapshot_date), event_status)
    )

    final = final_gameweeks(bootstrap, event_status)
    catch_up_gameweeks(client, settings, final, snapshot_date, result)
    return result


def catch_up_gameweeks(
    client: Client,
    settings: Settings,
    final: list[int],
    snapshot_date: date,
    result: ExtractResult,
) -> None:
    """Save live data and manager data for every final gameweek that is missing from disk.

    Checking what is missing (rather than only "the gameweek that just finished") means a
    missed day or a failed run heals itself on the next run.
    """
    raw = settings.raw_dir
    manager = settings.manager_id

    missing_live = [gw for gw in final if not already_saved(raw, "event_live", gw_key(gw))]
    for gw in missing_live:
        data = client.get(f"event/{gw}/live/")
        result.files_written.append(
            write_raw(raw_path(raw, "event_live", snapshot_date, gw_key(gw)), data)
        )

    # Manager data is refreshed when a new gameweek is final, when we have never fetched it,
    # or when a gameweek the manager played is still missing its picks.
    saved_history = latest_raw(raw, "entry_history")
    picks_gap = [
        gw
        for gw in final
        if gw in played_gameweeks(saved_history)
        and not already_saved(raw, "entry_picks", gw_key(gw))
    ]
    if not (missing_live or saved_history is None or picks_gap):
        return

    history = client.get(f"entry/{manager}/history/")
    result.files_written.append(write_raw(raw_path(raw, "entry_history", snapshot_date), history))
    transfers = client.get(f"entry/{manager}/transfers/")
    result.files_written.append(
        write_raw(raw_path(raw, "entry_transfers", snapshot_date), transfers)
    )

    played = played_gameweeks(history)
    for gw in final:
        if already_saved(raw, "entry_picks", gw_key(gw)):
            continue
        if gw not in played:
            result.notes.append(f"no picks for {gw_key(gw)}: manager had no team that week")
            continue
        try:
            picks = client.get(f"entry/{manager}/event/{gw}/picks/")
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                result.notes.append(f"picks for {gw_key(gw)} returned 404")
                continue
            raise
        result.files_written.append(
            write_raw(raw_path(raw, "entry_picks", snapshot_date, gw_key(gw)), picks)
        )


def backfill(
    client: Client,
    settings: Settings,
    snapshot_date: date | None = None,
    progress_every: int = 50,
) -> ExtractResult:
    """One-off history pull: the daily extract, then every player's element-summary.

    Players already saved (under any date) are skipped, so an interrupted backfill can simply
    be run again and carries on where it stopped.
    """
    snapshot_date = snapshot_date or today_utc()
    result = extract_daily(client, settings, snapshot_date)
    raw = settings.raw_dir

    bootstrap = read_raw(raw_path(raw, "bootstrap_static", snapshot_date))
    player_ids = sorted(p["id"] for p in bootstrap.get("elements", []))
    todo = [pid for pid in player_ids if not already_saved(raw, "element_summary", str(pid))]
    if len(todo) < len(player_ids):
        result.notes.append(f"skipped {len(player_ids) - len(todo)} players already saved")

    for i, pid in enumerate(todo, start=1):
        data = client.get(f"element-summary/{pid}/")
        result.files_written.append(
            write_raw(raw_path(raw, "element_summary", snapshot_date, str(pid)), data)
        )
        if progress_every and i % progress_every == 0:
            print(f"  element-summary: {i}/{len(todo)}", flush=True)
    return result
