-- One row per chip I have played, from entry/{id}/history/ "chips". Latest file only.

with source as (
    select snapshot_date, source_file, payload
    from {{ source('fpl_raw', 'entry_history') }}
    qualify snapshot_date = max(snapshot_date) over ()
),

chips as (
    select snapshot_date, source_file, unnest(json_extract(payload, '$.chips[*]')) as c
    from source
)

select
    (c ->> 'event')::integer as gameweek_id,
    c ->> 'name' as chip_name,
    (c ->> 'time')::timestamptz as played_at,
    snapshot_date,
    source_file
from chips
