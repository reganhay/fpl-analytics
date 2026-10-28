# FPL Analytics Pipeline — Design Document

Oct 28, 2026 · @Regan

## Purpose and learning goals

This project builds an end-to-end analytics pipeline on real Fantasy Premier League (FPL) data, so Regan can practise the tools and habits of an industry data analyst beyond his diploma. The finished project doubles as a portfolio piece for business analysis, operations and transformation roles.

By the end, Regan should be able to show he can:

- Extract data from an undocumented Application Programming Interface (API) and store it reliably over time
- Write Structured Query Language (SQL) to clean raw data and model it into a star schema
- Build a Power BI report with Power Query transformations and Data Analysis Expressions (DAX) measures
- Automate a scheduled data refresh and test data quality
- Turn analysis into a decision, act on it, and measure the outcome

The project is a learning exercise first. Claude Code builds the plumbing; Regan writes the analytical SQL and DAX himself (see Working agreement with Claude Code).

## Scope

Version 1 covers the 2026/27 Fantasy Premier League (FPL) season from today, plus a backfill of gameweeks already played. It runs on free tools only.

**In scope**

- Daily snapshots of player, team, price and ownership data
- Per-gameweek player performance, including backfilled history from gameweek 1
- Fixtures and fixture difficulty ratings
- Regan's own FPL team history and picks (via his manager ID)
- A SQL data model, automated data-quality tests and a Power BI report
- A short written findings report for the portfolio

**Out of scope for version 1**

- Previous seasons (the API only serves the current one; past seasons can be added later from community archives)
- Live in-match data during fixtures
- Machine-learning points prediction (a possible version 2 stretch goal)
- A public web app; the report lives in Power BI

## Data source

All data comes from the public Fantasy Premier League (FPL) Application Programming Interface (API) at `https://fantasy.premierleague.com/api/`. It needs no key or login, but it is unofficial and undocumented, so the pipeline must tolerate field changes. Endpoints below were confirmed working on 14 October 2026 ([source](https://dev.to/odeeb/fpl-api-endpoints-complete-reference-for-202627-5g3d)).

| Endpoint | What it gives us | Pull frequency |
| --- | --- | --- |
| `bootstrap-static/` | Every player (price, form, ownership, expected goals, injury news), all 20 teams, all 38 gameweeks | Daily |
| `fixtures/` | All 380 fixtures, scores, fixture difficulty, per-match stats | Daily |
| `event/{gw}/live/` | Every player's stats and points for one gameweek, with a points breakdown | Once per finished gameweek |
| `element-summary/{player_id}/` | One row per match this season per player, including price (`value`), ownership (`selected`) and net transfers | Once for backfill, then weekly |
| `event-status/` | Whether bonus points are added and the gameweek is final | Daily |
| `entry/{manager_id}/history/` | Regan's points, rank, team value and transfer costs per gameweek | Weekly |
| `entry/{manager_id}/event/{gw}/picks/` | Regan's 15 picks, captain and chip per gameweek | Weekly |
| `entry/{manager_id}/transfers/` | Every transfer Regan has made | Weekly |

**Quirks the code must handle**

- **The API only shows the present.** Today's prices and ownership overwrite yesterday's, so daily snapshots are the only way to build price and ownership history. The `element-summary` history gives a per-gameweek backfill for weeks already played.
- **Prices are in tenths of a million.** `now_cost: 61` means £6.1m.
- **Some numbers arrive as text.** `form`, `selected_by_percent`, `expected_goals` and `price_change_percent` must be cast to decimals.
- **Gameweeks are not final straight away.** Only treat a gameweek as final once `event-status/` shows bonus points added and leagues updated.
- **No published rate limit.** Send a descriptive User-Agent, pause about 0.5 seconds between calls, retry with back-off on errors.
- **Paths end with a slash.** Requests without the trailing slash fail.

**Open question:** Regan's FPL manager ID (shown in the URL of his Points page on the FPL website) goes in the config file.

## Architecture and tech stack

The pipeline follows the standard industry pattern of extract, load, then transform (ELT): raw data is saved untouched, then cleaned and modelled with Structured Query Language (SQL) inside a local warehouse. Every tool is free and widely used in analytics teams.

&#91;embedded content: pipeline architecture · 8 stages from API to report\]

GitHub Actions runs everything from Extract to Export each morning; Regan refreshes Power BI himself.

| Layer | Tool | Why this choice |
| --- | --- | --- |
| Language and packaging | Python 3.12, managed with `uv` | Fast, reproducible environments |
| Extraction | `requests` plus `tenacity` for retries | Simple, robust web requests with back-off |
| Raw storage | Gzipped JavaScript Object Notation (JSON) files, one folder per date | An untouched audit trail; any model can be rebuilt from it |
| Warehouse | DuckDB (a single local database file) | Full SQL, very fast, no server to run |
| Transformation and tests | dbt (data build tool) with the `dbt-duckdb` adapter | The industry standard for SQL modelling, documentation and data tests |
| Hand-off to Power BI | Parquet files exported from the final tables | Power BI Desktop reads Parquet natively, with no drivers to install |
| Reporting | Power BI Desktop | The target tool for Regan's job market |
| Scheduling | GitHub Actions on a daily timer | Snapshots keep running when Regan's computer is off |
| Version control | Git and GitHub | Portfolio visibility and change history |

Data moves through three layers, named the way dbt projects usually name them:

1. **Raw:** JSON exactly as the API returned it, never edited.
2. **Staging:** one cleaned table per source, with correct data types, renamed columns and prices in pounds.
3. **Marts:** the star schema Power BI reads (see Data model).

## Data model

The marts layer is a star schema: fact tables hold measurable events, and dimension tables describe them. Every fact table states its grain (what one row means), because getting the grain wrong is the most common modelling mistake.

| Table | Type | Grain (one row per…) | Key columns | Built from |
| --- | --- | --- | --- | --- |
| `dim_player` | Dimension (history-tracked) | Player per period they belonged to a club | player\_key, player\_id, web\_name, position, team\_id, valid\_from, valid\_to, is\_current | Daily snapshots |
| `dim_team` | Dimension | Premier League club | team\_id, name, short\_name, home and away strength | `bootstrap-static` |
| `dim_gameweek` | Dimension | Gameweek | gameweek\_id, deadline\_time, is\_finished, is\_final | `bootstrap-static`, `event-status` |
| `dim_date` | Dimension | Calendar day | date, weekday, month, gameweek\_id (the gameweek whose deadline is next) | Generated by a Structured Query Language (SQL) model |
| `fct_player_daily` | Fact (snapshot) | Player per day | player\_key, date, price\_gbp, selected\_pct, form, transfers\_in\_event, transfers\_out\_event, status, chance\_of\_playing | Daily snapshots |
| `fct_player_match` | Fact | Player per fixture | player\_key, fixture\_id, gameweek\_id, minutes, total\_points, goals, assists, expected\_goals, expected\_assists, bonus, bps, price\_gbp, selected | `element-summary`, `event/{gw}/live` |
| `fct_fixture` | Fact | Fixture | fixture\_id, gameweek\_id, home\_team\_id, away\_team\_id, scores, home and away difficulty, kickoff\_time | `fixtures` |
| `fct_my_gameweek` | Fact | Regan's team per gameweek | gameweek\_id, points, total\_points, overall\_rank, bank\_gbp, team\_value\_gbp, transfers, transfer\_cost, bench\_points | `entry/{id}/history` |
| `fct_my_pick` | Fact | Pick per gameweek | gameweek\_id, player\_key, squad\_position, multiplier, is\_captain | `entry/{id}/event/{gw}/picks` |
| `fct_my_transfer` | Fact | Transfer | gameweek\_id, player\_in\_key, player\_out\_key, price\_in\_gbp, price\_out\_gbp, transfer\_time | `entry/{id}/transfers` |

**Design rules**

- **Player per fixture, not per gameweek.** Double gameweeks mean a player can play twice in one gameweek; aggregating to gameweek happens in Power BI measures, not in the table.
- **History-tracked players.** A player who moves club in January keeps his old club against his old matches. dbt (data build tool) snapshots manage this (a slowly changing dimension, type 2).
- **Surrogate keys.** Facts join to `dim_player` on `player_key`, not the raw API ID, so history stays correct.
- **Money in pounds.** Staging divides every price by 10 once; nothing downstream sees tenths.

## Pipeline

One command-line tool, `fpl`, runs each stage, and every stage is safe to re-run: running it twice on the same day overwrites rather than duplicates.

1. **Extract (`fpl extract daily`).** Call `bootstrap-static/`, `fixtures/` and `event-status/`. Save each response as `data/raw/<endpoint>/<YYYY-MM-DD>.json.gz`. If a gameweek has just become final, also save `event/{gw}/live/` and Regan's picks for that gameweek.
2. **Backfill (`fpl backfill`).** Run once at the start. Loop through every player's `element-summary/` (about 670 calls, 0.5 seconds apart, roughly 6 minutes) and every finished gameweek's `live` and picks data. Re-runnable if interrupted.
3. **Load (`fpl load`).** Read every raw file into DuckDB raw tables, adding `snapshot_date` and `source_file` columns so every row can be traced back to its file.
4. **Transform and test (`dbt build`).** Build staging models, the player history snapshot and the marts, then run every data test. A failing test stops the run.
5. **Export (`fpl export`).** Write each mart table to `data/marts/<table>.parquet` for Power BI.
6. **Schedule.** A GitHub Actions workflow runs steps 1, 3, 4 and 5 every morning at about 06:00 UK time, after the overnight price changes. It commits new raw files and Parquet files back to the repository and emails Regan if anything fails.
7. **Refresh.** Regan pulls the latest repository and presses Refresh in Power BI Desktop.

**Logging and config**

- Settings live in `config.toml`: manager ID, request delay, User-Agent, data paths.
- Each run writes a one-line summary to `data/run_log.csv` (timestamp, stage, rows written, status). This becomes a small dataset of its own for a pipeline-health page in the report.

## Data quality checks

Every check below is a dbt (data build tool) test that runs on each build, so bad data fails loudly instead of reaching the report.

| Check | Applies to | What it catches |
| --- | --- | --- |
| Unique and not null | Every primary key | Duplicate or missing rows |
| Unique combination | `fct_player_daily` (player, date); `fct_player_match` (player, fixture) | Grain violations, such as a snapshot loaded twice |
| Relationships | Every foreign key to its dimension | Orphan rows, such as a player ID with no player |
| Accepted values | `position` in GKP, DEF, MID, FWD; `status` codes | Unexpected categories after an API change |
| Range | `price_gbp` between 3.5 and 16.0; `selected_pct` between 0 and 100; `minutes` between 0 and 100 per match | Unit errors, such as forgetting to divide by 10 |
| Freshness | Latest `snapshot_date` | The schedule silently stopping (warn after 2 days) |
| Row counts | 20 teams, 38 gameweeks, 380 fixtures | Truncated or partial pulls |
| Reconciliation | Regan's pick points × multipliers, after automatic substitutions, equal his gameweek points from `history` | Errors in joins or multiplier logic |
| Schema drift | Raw field list compared with the last run | New or removed API fields (warning only) |

The range limits are starting assumptions; Regan should adjust them once he has looked at the real data.

## Power BI report design

The report has six pages, each answering one question. Regan builds this part himself; Claude Code only prepares the Parquet files and a starter list of measures to write.

| Page | Question it answers | Main visuals |
| --- | --- | --- |
| 1. Season overview | How is my team doing? | Cards for points, rank and team value; rank over gameweeks line chart |
| 2. Player value | Who gives the most points per £1m? | Scatter of price against points, coloured by position; top-10 table with slicers |
| 3. Price and ownership | Whose price is about to move, and does ownership follow points? | Daily price and ownership lines; net transfers bar chart |
| 4. Fixtures | Which teams have the easiest run ahead? | Matrix of team by next 6 gameweeks, conditionally formatted by difficulty |
| 5. My decisions | Did my transfers and captain picks pay off? | Points of player bought against player sold over the following 4 gameweeks; captain points against best available |
| 6. Pipeline health | Is the data fresh and complete? | Last run time, rows per day, failed runs (from `run_log.csv`) |

**Data Analysis Expressions (DAX) measures to write**

- Total Points, Points per Match, Points per 90 Minutes
- Points per £1m (points divided by current price)
- Expected Goal Involvement per 90 (expected goals plus expected assists)
- Form: average points over the last 4 finished gameweeks
- Price Change Since Gameweek 1, Ownership Change Last 7 Days
- Transfer Gain: points of player in minus points of player out, over the next 4 gameweeks
- Captain Points Lost: best possible captain score minus actual captain score
- Rank Change from previous gameweek

**Skills each page deliberately exercises**

- **Role-playing dimension:** `fct_fixture` links to `dim_team` twice (home and away). One relationship stays inactive and is switched on in DAX with `USERELATIONSHIP`.
- **Time intelligence:** a marked date table (`dim_date`) for rolling 7-day and 4-gameweek measures.
- **Power Query:** `run_log.csv` is loaded raw and cleaned in Power Query, so that skill is practised too. A `DataFolder` parameter holds the path to the Parquet files.
- **Report craft:** drill-through from any player to a player detail page, a tooltip page, and bookmarks to switch between views.

## Analysis questions and portfolio outputs

The project ends with a findings report that answers real questions and shows a decision changed by data. Each question below has a business equivalent, which is how it should be framed in interviews.

| Question | Business equivalent | Method |
| --- | --- | --- |
| Which positions and price bands give the best points per £1m? | Return on investment by product line | Group and compare in Structured Query Language (SQL), then Power BI |
| Does rising ownership come before or after a price rise? | Leading and lagging indicators | Daily time series, lagged comparison |
| Do expected goals predict future points better than past points do? | Choosing which metric to forecast with | Correlation over rolling windows in Python (pandas) |
| How much does fixture difficulty really change expected points? | Testing an assumption the business relies on | Grouped averages with confidence intervals |
| Are my transfers beating a do-nothing baseline? | Measuring the impact of a change | Compare against a control: points if no transfer had been made |

**Portfolio deliverables**

- [ ] A public GitHub repository with a clear README, architecture diagram and setup instructions
- [ ] dbt (data build tool) documentation site showing the model lineage
- [ ] The Power BI file plus screenshots of each page
- [ ] A two-page findings write-up: question, method, result, decision taken, measured outcome
- [ ] A short LinkedIn post summarising one finding

## Repository structure and conventions

One repository, `fpl-analytics`, holds code, models and data, laid out so a recruiter can find their way around in a minute.

```text
fpl-analytics/
├── README.md                 # what it is, the diagram, how to run it
├── CLAUDE.md                 # this design doc's key rules, for Claude Code
├── config.toml               # manager ID, delay, paths
├── pyproject.toml            # dependencies (managed by uv)
├── src/fpl/
│   ├── client.py             # API calls, retries, User-Agent
│   ├── extract.py            # daily pull and backfill
│   ├── load.py               # raw files into DuckDB
│   ├── export.py             # marts to Parquet
│   └── cli.py                # the `fpl` command
├── tests/                    # pytest, using saved sample responses
├── dbt/
│   ├── models/staging/       # stg_* models (Claude Code)
│   ├── models/marts/         # dim_* and fct_* models (Regan)
│   ├── snapshots/            # player history
│   └── tests/                # custom data tests
├── data/
│   ├── raw/<endpoint>/<date>.json.gz
│   ├── marts/*.parquet
│   └── run_log.csv
├── powerbi/fpl-report.pbix
├── analysis/                 # Jupyter notebooks for the Python questions
├── docs/findings.md          # the portfolio write-up
└── .github/workflows/daily.yml
```

**Conventions**

- Python: type hints, `ruff` for formatting and linting, `pytest` with saved Application Programming Interface (API) responses (never live calls in tests).
- Structured Query Language (SQL): lowercase keywords, one model per file, `stg_`, `dim_`, `fct_` prefixes, every model documented in a `.yml` file.
- Commits: small and descriptive, one stage at a time.
- The DuckDB file is rebuilt from raw data and is not committed.

## Working agreement with Claude Code

Claude Code builds the infrastructure and acts as a tutor for the analytics. If it writes the analysis too, Regan learns nothing he can defend in an interview.

| Area | Claude Code | Regan |
| --- | --- | --- |
| Python extraction, loading, export, command-line tool | Builds and tests it | Reviews it and runs it |
| GitHub Actions schedule | Builds it | Sets it live |
| dbt (data build tool) project set-up and staging models | Builds it, explaining each choice | Reads every model |
| Marts: dimension and fact models | Reviews, hints, writes tests | **Writes the Structured Query Language (SQL)** |
| Player history snapshot | Explains the concept, reviews | Writes it |
| Power BI model, Data Analysis Expressions (DAX) and visuals | Explains and reviews pasted DAX | **Builds all of it** |
| Python analysis notebooks | Suggests methods, reviews | Writes them |
| Findings write-up | Critiques the draft | Writes it |

**Instructions for Claude Code (copy into `CLAUDE.md`)**

- Treat this document as the specification. Ask before changing the architecture or adding a dependency.
- Build in the order set out in Build plan. Finish and test one stage before starting the next.
- For anything in Regan's column, do not write the solution. Give a hint first, then a partial example if asked, and the full answer only when Regan explicitly asks for it.
- When reviewing Regan's SQL or DAX, point out bugs, grain problems and clearer alternatives, and explain why.
- Explain new concepts in plain language with a short example, as if to a strong beginner.
- Be polite to the Fantasy Premier League Application Programming Interface (API): cache responses, keep the delay between calls, and never call it from tests.
- Spell out acronyms in full on first use, then use the short form.

## Build plan

Six milestones, in order. Milestones 1 and 2 come first because every day without a snapshot is history lost.

&#91;embedded content: build plan · 6 milestones, each with its done-when gate\]

Each milestone finishes only when its gate passes; Claude Code should not start the next one until then.

**First prompt to give Claude Code**

```text
Read docs/design.md (the FPL analytics design document). Summarise the plan back to me in five bullet points, list anything unclear, then set up the repository structure and start Milestone 1. Follow the working agreement: you build the pipeline, I write the marts SQL and all Power BI work.
```

## Risks and constraints

The biggest risk is lost history: a day the snapshot misses is gone for good, so the daily schedule should be live within the first week.

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Missed daily snapshots | Permanent gaps in price and ownership history | Set the GitHub Actions schedule live early; freshness test plus failure emails |
| The Fantasy Premier League (FPL) Application Programming Interface (API) changes or blocks requests | Pipeline breaks | Raw files kept untouched; schema-drift warning; polite request rate |
| Power BI Desktop runs only on Windows | Cannot build the report on a Mac | Use a Windows PC or a Windows virtual machine; check this before Milestone 5 |
| Publishing to the Power BI web service needs a work or school account | Cannot share a live report link | Share the .pbix file, screenshots and a recorded walkthrough instead |
| Repository grows with daily raw files | Slow clones over a full season | Gzip every file; review size at the end of each month; move raw data to a separate branch if it passes 500 MB |
| Claude Code writes the analysis for Regan | The learning goal is lost | Working agreement above, written into `CLAUDE.md` |
| Scope creep, such as machine learning or a web app | Project stalls before the report exists | Version 1 scope is fixed; extras go on a version 2 list |

**Open questions**

- Regan's FPL manager ID: 2244018
- Does Regan have a Windows machine for Power BI Desktop?: Yes
