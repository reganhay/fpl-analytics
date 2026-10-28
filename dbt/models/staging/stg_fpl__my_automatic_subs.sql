-- One row per automatic substitution in my team, from entry/{id}/event/{gw}/picks/.
-- When a starter plays 0 minutes, FPL swaps in the first eligible bench player.

with source as (
    select snapshot_date, entity_key, source_file, payload
    from {{ source('fpl_raw', 'entry_picks') }}
    qualify snapshot_date = max(snapshot_date) over (partition by entity_key)
),

subs as (
    select
        snapshot_date,
        source_file,
        substr(entity_key, 3)::integer as gameweek_id,
        unnest(json_extract(payload, '$.automatic_subs[*]')) as s
    from source
)

select
    gameweek_id,
    (s ->> 'element_in')::integer as player_in_id,
    (s ->> 'element_out')::integer as player_out_id,
    snapshot_date,
    source_file
from subs
