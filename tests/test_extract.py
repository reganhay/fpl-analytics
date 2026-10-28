from __future__ import annotations

from datetime import date

from conftest import FakeClient, default_routes, sample

from fpl.extract import backfill, extract_daily, final_gameweeks, raw_path, read_raw

DAY1 = date(2026, 10, 28)
DAY2 = date(2026, 10, 29)


def test_final_gameweeks_holds_back_unsettled_current_week() -> None:
    bootstrap = sample("bootstrap_static")
    assert final_gameweeks(bootstrap, sample("event_status")) == [1, 2]
    assert final_gameweeks(bootstrap, sample("event_status_settled")) == [1, 2, 3]


def test_daily_writes_core_snapshots(settings) -> None:
    client = FakeClient(default_routes())
    extract_daily(client, settings, DAY1)

    for endpoint in ("bootstrap_static", "fixtures", "event_status"):
        path = raw_path(settings.raw_dir, endpoint, DAY1)
        assert path.exists()
    stored = read_raw(raw_path(settings.raw_dir, "bootstrap_static", DAY1))
    assert stored == sample("bootstrap_static"), "raw data must be saved untouched"


def test_daily_catches_up_final_gameweeks_and_skips_unplayed_picks(settings) -> None:
    client = FakeClient(default_routes())
    result = extract_daily(client, settings, DAY1)

    raw = settings.raw_dir
    assert raw_path(raw, "event_live", DAY1, "gw01").exists()
    assert raw_path(raw, "event_live", DAY1, "gw02").exists()
    assert not raw_path(raw, "event_live", DAY1, "gw03").exists(), "gw3 is not settled yet"
    # Manager joined in gw2, so gw1 picks are skipped without calling the API.
    assert "entry/2244018/event/1/picks/" not in client.calls
    assert raw_path(raw, "entry_picks", DAY1, "gw02").exists()
    assert any("gw01" in note for note in result.notes)


def test_daily_rerun_same_day_overwrites_without_refetching_gameweeks(settings) -> None:
    extract_daily(FakeClient(default_routes()), settings, DAY1)
    client = FakeClient(default_routes())
    result = extract_daily(client, settings, DAY1)

    assert client.calls == ["bootstrap-static/", "fixtures/", "event-status/"]
    assert len(result.files_written) == 3
    assert len(list((settings.raw_dir / "bootstrap_static").iterdir())) == 1


def test_next_day_picks_up_newly_settled_gameweek(settings) -> None:
    extract_daily(FakeClient(default_routes()), settings, DAY1)
    routes = default_routes()
    routes["event-status/"] = sample("event_status_settled")
    client = FakeClient(routes)
    extract_daily(client, settings, DAY2)

    raw = settings.raw_dir
    assert raw_path(raw, "event_live", DAY2, "gw03").exists()
    assert raw_path(raw, "entry_picks", DAY2, "gw03").exists()
    assert raw_path(raw, "entry_history", DAY2).exists()
    assert "event/1/live/" not in client.calls


def test_backfill_saves_every_player_and_resumes(settings) -> None:
    routes = default_routes()
    del routes["element-summary/201/"]  # simulate the run dying part-way through
    try:
        backfill(FakeClient(routes), settings, DAY1, progress_every=0)
    except Exception:
        pass

    client = FakeClient(default_routes())
    result = backfill(client, settings, DAY1, progress_every=0)

    summaries = [c for c in client.calls if c.startswith("element-summary/")]
    assert summaries == ["element-summary/201/"]
    assert any("skipped 2 players" in note for note in result.notes)
    assert raw_path(settings.raw_dir, "element_summary", DAY1, "201").exists()
