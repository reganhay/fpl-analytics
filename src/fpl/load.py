"""Load every raw file into DuckDB, one raw table per endpoint and one row per file.

Each raw table has the same four columns:

    snapshot_date  the date folder or file name the response was saved under
    entity_key     the per-file key for keyed endpoints (gw07, a player ID), else null
    source_file    the file's path under the raw folder, so every row traces back to it
    payload        the untouched JSON response

Nothing is renamed or cast here; that is the job of the dbt staging models. Tables are
rebuilt from scratch on every run, so loading twice gives the same result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import duckdb

from fpl.config import Settings

ENDPOINTS = [
    "bootstrap_static",
    "fixtures",
    "event_status",
    "event_live",
    "element_summary",
    "entry_history",
    "entry_transfers",
    "entry_picks",
]

EMPTY_TABLE = "(snapshot_date date, entity_key varchar, source_file varchar, payload json)"

LOAD_SQL = r"""
create or replace table raw.{table} as
with files as (
    select replace(filename, '\', '/') as path, json as payload
    from read_json_objects(
        '{glob}', format = 'unstructured', filename = true, maximum_object_size = 67108864
    )
)
select
    cast(regexp_extract(path, '/(\d{{4}}-\d{{2}}-\d{{2}})(/[^/]+)?\.json\.gz$', 1) as date)
        as snapshot_date,
    nullif(regexp_extract(path, '/\d{{4}}-\d{{2}}-\d{{2}}/([^/]+)\.json\.gz$', 1), '')
        as entity_key,
    regexp_extract(path, '.*/({table}/.+)$', 1) as source_file,
    payload
from files
order by snapshot_date, entity_key
"""


@dataclass
class LoadResult:
    rows_by_table: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def rows_written(self) -> int:
        return sum(self.rows_by_table.values())


def load(settings: Settings) -> LoadResult:
    result = LoadResult()
    settings.warehouse.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(settings.warehouse)) as con:
        con.execute("create schema if not exists raw")
        for table in ENDPOINTS:
            folder = settings.raw_dir / table
            if not any(folder.rglob("*.json.gz")):
                # An empty table keeps the dbt sources valid before an endpoint has any files.
                con.execute(f"create or replace table raw.{table} {EMPTY_TABLE}")
                result.notes.append(f"no files for {table}")
            else:
                con.execute(LOAD_SQL.format(table=table, glob=_glob(folder)))
            result.rows_by_table[table] = con.execute(
                f"select count(*) from raw.{table}"
            ).fetchone()[0]
    return result


def _glob(folder: Path) -> str:
    return (folder.as_posix() + "/**/*.json.gz").replace("'", "''")
