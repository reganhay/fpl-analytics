from __future__ import annotations

from datetime import date

import duckdb
from conftest import FakeClient, default_routes

from fpl.extract import extract_daily
from fpl.load import load


def test_load_one_row_per_file_with_lineage(settings) -> None:
    extract_daily(FakeClient(default_routes()), settings, date(2026, 10, 28))
    result = load(settings)

    assert result.rows_by_table["bootstrap_static"] == 1
    assert result.rows_by_table["event_live"] == 2  # gw1 and gw2 are final in the samples
    assert result.rows_by_table["element_summary"] == 0
    assert "no files for element_summary" in result.notes

    with duckdb.connect(str(settings.warehouse)) as con:
        rows = con.execute(
            "select snapshot_date, entity_key, source_file, payload->>'$.elements[0].id' "
            "from raw.event_live order by entity_key"
        ).fetchall()
    assert rows[0] == (date(2026, 10, 28), "gw01", "event_live/2026-10-28/gw01.json.gz", "102")


def test_load_is_repeatable(settings) -> None:
    extract_daily(FakeClient(default_routes()), settings, date(2026, 10, 28))
    first = load(settings).rows_by_table
    second = load(settings).rows_by_table
    assert first == second
