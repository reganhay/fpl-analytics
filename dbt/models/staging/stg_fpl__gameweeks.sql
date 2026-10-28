-- One row per gameweek per daily snapshot, from bootstrap-static.
-- is_finished and is_data_checked change over time, which is why every snapshot is kept.

with source as (
    select snapshot_date, source_file, payload
    from {{ source('fpl_raw', 'bootstrap_static') }}
),

gameweeks as (
    select snapshot_date, source_file, unnest(json_extract(payload, '$.events[*]')) as e
    from source
)

select
    snapshot_date,
    (e ->> 'id')::integer as gameweek_id,
    e ->> 'name' as gameweek_name,
    (e ->> 'deadline_time')::timestamptz as deadline_time,
    (e ->> 'finished')::boolean as is_finished,
    (e ->> 'data_checked')::boolean as is_data_checked,
    (e ->> 'is_previous')::boolean as is_previous,
    (e ->> 'is_current')::boolean as is_current,
    (e ->> 'is_next')::boolean as is_next,
    (e ->> 'average_entry_score')::integer as average_score,
    (e ->> 'highest_score')::integer as highest_score,
    (e ->> 'top_element')::integer as top_player_id,
    (e ->> 'most_captained')::integer as most_captained_player_id,
    (e ->> 'most_selected')::integer as most_selected_player_id,
    (e ->> 'transfers_made')::integer as transfers_made,
    source_file
from gameweeks
