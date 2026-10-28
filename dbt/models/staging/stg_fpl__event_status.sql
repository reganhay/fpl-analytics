-- One row per match day of the current gameweek per daily snapshot, from event-status/.
-- A gameweek is final when every row has bonus added and leagues_status is 'Updated'.

with source as (
    select snapshot_date, source_file, payload
    from {{ source('fpl_raw', 'event_status') }}
),

statuses as (
    select
        snapshot_date,
        source_file,
        payload ->> 'leagues' as leagues_status,
        unnest(json_extract(payload, '$.status[*]')) as s
    from source
)

select
    snapshot_date,
    (s ->> 'event')::integer as gameweek_id,
    (s ->> 'date')::date as match_date,
    (s ->> 'bonus_added')::boolean as is_bonus_added,
    s ->> 'points' as points_status,
    leagues_status,
    source_file
from statuses
