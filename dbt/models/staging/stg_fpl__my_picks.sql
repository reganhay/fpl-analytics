-- One row per player in my 15-man squad per gameweek, from entry/{id}/event/{gw}/picks/.
-- squad_position 1-11 is the starting XI, 12-15 the bench in order.
-- multiplier is as the squad was picked: 0 on the bench, 2 for the captain (3 with triple
-- captain). Automatic substitutions are in stg_fpl__my_automatic_subs, not applied here.

with source as (
    select snapshot_date, entity_key, source_file, payload
    from {{ source('fpl_raw', 'entry_picks') }}
),

picks as (
    select
        snapshot_date,
        source_file,
        substr(entity_key, 3)::integer as gameweek_id,
        payload ->> 'active_chip' as active_chip,
        unnest(json_extract(payload, '$.picks[*]')) as p
    from source
)

select
    gameweek_id,
    (p ->> 'element')::integer as player_id,
    (p ->> 'position')::integer as squad_position,
    (p ->> 'multiplier')::integer as multiplier,
    (p ->> 'is_captain')::boolean as is_captain,
    (p ->> 'is_vice_captain')::boolean as is_vice_captain,
    active_chip,
    snapshot_date,
    source_file
from picks
qualify row_number() over (partition by gameweek_id, player_id order by snapshot_date desc) = 1
