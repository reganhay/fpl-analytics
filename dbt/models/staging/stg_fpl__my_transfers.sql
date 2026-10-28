-- One row per transfer I have made, from entry/{id}/transfers/. Latest file only,
-- since each file holds the full list. Prices converted from tenths to pounds.

with source as (
    select snapshot_date, source_file, payload
    from {{ source('fpl_raw', 'entry_transfers') }}
    qualify snapshot_date = max(snapshot_date) over ()
),

transfers as (
    select snapshot_date, source_file, unnest(json_extract(payload, '$[*]')) as t
    from source
)

select
    (t ->> 'event')::integer as gameweek_id,
    (t ->> 'time')::timestamptz as transferred_at,
    (t ->> 'element_in')::integer as player_in_id,
    (t ->> 'element_out')::integer as player_out_id,
    ((t ->> 'element_in_cost')::integer / 10)::decimal(5, 1) as price_in_gbp,
    ((t ->> 'element_out_cost')::integer / 10)::decimal(5, 1) as price_out_gbp,
    snapshot_date,
    source_file
from transfers
