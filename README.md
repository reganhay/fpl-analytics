# FPL Analytics

An end-to-end analytics pipeline on real Fantasy Premier League (FPL) data: daily extraction from
the public FPL API, a DuckDB warehouse modelled with dbt into a star schema, automated
data-quality tests, and a Power BI report.

The full specification is in [docs/design.md](docs/design.md).

Raw data is kept untouched, so everything after it can be rebuilt.

```text
FPL API ──► Extract ──────────► Raw files ──────────► Warehouse
public,     Python fpl command  gzipped JSON by date  DuckDB raw tables
no key                                                    │
   ┌──────────────────────────────────────────────────────┘
   ▼
Staging ──────► Marts ─────────────► Export ─────────► Power BI
dbt stg_ models star schema, tests   Parquet files     report, Regan builds
```

## Status

| Milestone | Owner | Done when | State |
| --- | --- | --- | --- |
| 1. Extraction client | Claude Code | `fpl extract daily` saves today's raw files | Code and tests done; awaiting first live run |
| 2. Schedule and backfill | Claude Code | Daily runs pass 2 days running; backfill full | Workflow built; awaiting go-live |
| 3. Load and staging | Claude Code | `dbt build` passes with staging tests green | Not started |
| 4. Marts and snapshot | Regan | Star schema and reconciliation tests pass | Not started |
| 5. Power BI report | Regan | All six pages and measures work | Not started |
| 6. Analysis and write-up | Regan | Findings, README and post are published | Not started |

## Setup

Requires Python 3.12+. The project is managed with [uv](https://docs.astral.sh/uv/):

```powershell
uv sync                 # create .venv and install dependencies
uv run pytest           # run the tests (no live API calls)
```

Without uv, a plain virtual environment works too:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e . pytest ruff
```

Set your FPL manager ID in [config.toml](config.toml).

## Usage

```powershell
uv run fpl extract daily   # today's snapshot, plus any newly final gameweek data
uv run fpl backfill        # one-off: every player's match history (~670 calls, ~6 minutes)
```

Both commands are safe to re-run: a second run on the same day overwrites rather than duplicates,
and an interrupted backfill carries on from where it stopped. Each run appends a line to
`data/run_log.csv`.

## Daily schedule

[.github/workflows/daily.yml](.github/workflows/daily.yml) runs every morning at 06:00 UTC
(06:00 UK in winter, 07:00 in summer). It runs the tests, runs `fpl extract daily`, and commits
the new raw files and run-log line back to the repository. GitHub emails you if a scheduled run
fails.

To run it by hand, or to run the backfill in the cloud: **Actions → daily → Run workflow**, then
pick `extract daily` or `backfill`.

## Raw data layout

```text
data/raw/
├── bootstrap_static/2026-10-28.json.gz      # players, teams, gameweeks (daily)
├── fixtures/2026-10-28.json.gz              # all fixtures (daily)
├── event_status/2026-10-28.json.gz          # is the gameweek final? (daily)
├── entry_history/2026-10-28.json.gz         # my season history (each new final gameweek)
├── entry_transfers/2026-10-28.json.gz       # my transfers (each new final gameweek)
├── event_live/2026-10-28/gw07.json.gz       # every player's stats for one final gameweek
├── entry_picks/2026-10-28/gw07.json.gz      # my 15 picks for one final gameweek
└── element_summary/2026-10-28/123.json.gz   # one player's per-match history (backfill)
```

Files are stored exactly as the API returned them. Everything downstream can be rebuilt from here.
