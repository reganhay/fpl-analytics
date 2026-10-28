from __future__ import annotations

import csv

from conftest import FakeClient, default_routes

from fpl import cli


def test_run_stage_logs_success_and_failure(settings, monkeypatch) -> None:
    monkeypatch.setattr(cli, "make_client", lambda s: FakeClient(default_routes()))
    assert cli.run_stage(settings, "extract_daily", cli.extract_daily) == 0

    monkeypatch.setattr(cli, "make_client", lambda s: FakeClient({}))
    assert cli.run_stage(settings, "extract_daily", cli.extract_daily) == 1

    with settings.run_log.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [r["status"] for r in rows] == ["success", "failed"]
    assert int(rows[0]["rows_written"]) > 0
    assert "HTTPError" in rows[1]["detail"]
