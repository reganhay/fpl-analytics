"""Shared test helpers. Tests never call the live FPL API; they use saved sample responses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import requests

from fpl.config import Settings

SAMPLES = Path(__file__).parent / "sample_responses"


def sample(name: str) -> Any:
    return json.loads((SAMPLES / f"{name}.json").read_text(encoding="utf-8"))


class FakeClient:
    """Stands in for FPLClient. Maps request paths to canned responses and records every call."""

    def __init__(self, routes: dict[str, Any]) -> None:
        self.routes = routes
        self.calls: list[str] = []

    def get(self, path: str) -> Any:
        self.calls.append(path)
        if path not in self.routes:
            response = requests.Response()
            response.status_code = 404
            raise requests.HTTPError(f"404 for {path}", response=response)
        return self.routes[path]


def default_routes(manager_id: int = 2244018) -> dict[str, Any]:
    routes: dict[str, Any] = {
        "bootstrap-static/": sample("bootstrap_static"),
        "fixtures/": sample("fixtures"),
        "event-status/": sample("event_status"),
        f"entry/{manager_id}/history/": sample("entry_history"),
        f"entry/{manager_id}/transfers/": sample("entry_transfers"),
    }
    for gw in (1, 2, 3):
        routes[f"event/{gw}/live/"] = sample("event_live")
        routes[f"entry/{manager_id}/event/{gw}/picks/"] = sample("entry_picks")
    for pid in (101, 102, 201):
        routes[f"element-summary/{pid}/"] = sample("element_summary")
    return routes


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        manager_id=2244018,
        base_url="https://fantasy.premierleague.com/api/",
        user_agent="fpl-analytics-tests",
        request_delay=0,
        timeout=5,
        max_attempts=3,
        raw_dir=tmp_path / "raw",
        marts_dir=tmp_path / "marts",
        warehouse=tmp_path / "fpl.duckdb",
        run_log=tmp_path / "run_log.csv",
    )
