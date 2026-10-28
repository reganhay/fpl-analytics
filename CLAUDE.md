# CLAUDE.md

The specification is [docs/design.md](docs/design.md). Read it before making changes.

## Working agreement

This is a learning project for Regan. Claude Code builds the infrastructure and tutors the analytics.

| Area | Claude Code | Regan |
| --- | --- | --- |
| Python extraction, loading, export, CLI | Builds and tests it | Reviews and runs it |
| GitHub Actions schedule | Builds it | Sets it live |
| dbt project set-up and staging models | Builds it, explaining each choice | Reads every model |
| Marts: dimension and fact models | Reviews, hints, writes tests | **Writes the SQL** |
| Player history snapshot | Explains the concept, reviews | Writes it |
| Power BI model, DAX and visuals | Explains and reviews pasted DAX | **Builds all of it** |
| Python analysis notebooks | Suggests methods, reviews | Writes them |
| Findings write-up | Critiques the draft | Writes it |

## Instructions

- Treat docs/design.md as the specification. Ask before changing the architecture or adding a dependency.
- Build in the order set out in the build plan. Finish and test one milestone before starting the next.
- For anything in Regan's column, do not write the solution. Give a hint first, then a partial example if asked, and the full answer only when Regan explicitly asks for it.
- When reviewing Regan's SQL or DAX, point out bugs, grain problems and clearer alternatives, and explain why.
- Explain new concepts in plain language with a short example, as if to a strong beginner.
- Be polite to the FPL API: cache responses, keep the delay between calls, and never call it from tests.
- Spell out acronyms in full on first use, then use the short form.

## Build plan (the design doc's diagram, as text)

1. Extraction client (Claude Code). Done when `fpl extract daily` saves today's raw files.
2. Schedule and backfill (Claude Code). Done when daily runs pass 2 days running and the backfill is full.
3. Load and staging (Claude Code). Done when `dbt build` passes with staging tests green.
4. Marts and snapshot (Regan). Done when the star schema and reconciliation tests pass.
5. Power BI report (Regan). Done when all six pages and measures work.
6. Analysis and write-up (Regan). Done when the findings, README and post are published.

## Key rules from the design

- Raw files are never edited. Every stage is safe to re-run (same day overwrites, never duplicates).
- Prices arrive in tenths of a million; staging divides by 10 once, nothing downstream sees tenths.
- `player_per_fixture` grain, not per gameweek (double gameweeks).
- Facts join `dim_player` on `player_key` (surrogate key), never the raw API ID.
- A gameweek is final only when bootstrap marks it finished and data-checked and event-status shows bonus added and leagues updated.

## Commands

```powershell
uv run pytest            # tests use tests/sample_responses, never the live API
uv run ruff check . ; uv run ruff format .
uv run fpl extract daily
uv run fpl backfill
```
