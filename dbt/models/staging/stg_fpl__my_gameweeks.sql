-- One row per gameweek of my FPL team, from entry/{id}/history/ "current".
-- Each saved file holds the whole season so far, so only the latest file is used.
-- bank and value arrive in tenths of a million, like player prices.

with source as (
    select snapshot_date, source_file, payload
    from {{ source('fpl_raw', 'entry_history') }}
    qualify snapshot_date = max(snapshot_date) over ()
),

gameweeks as (
    select snapshot_date, source_file, unnest(json_extract(payload, '$.current[*]')) as g
    from source
)

select
    (g ->> 'event')::integer as gameweek_id,
    (g ->> 'points')::integer as points,
    (g ->> 'total_points')::integer as total_points,
    (g ->> 'rank')::integer as gameweek_rank,
    (g ->> 'overall_rank')::integer as overall_rank,
    (g ->> 'percentile_rank')::integer as percentile_rank,
    ((g ->> 'bank')::integer / 10)::decimal(5, 1) as bank_gbp,
    ((g ->> 'value')::integer / 10)::decimal(5, 1) as team_value_gbp,
    (g ->> 'event_transfers')::integer as transfers,
    (g ->> 'event_transfers_cost')::integer as transfer_cost,
    (g ->> 'points_on_bench')::integer as bench_points,
    snapshot_date,
    source_file
from gameweeks
