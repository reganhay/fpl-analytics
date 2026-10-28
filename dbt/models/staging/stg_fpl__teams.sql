-- One row per Premier League club per daily snapshot, from bootstrap-static.

with source as (
    select snapshot_date, source_file, payload
    from {{ source('fpl_raw', 'bootstrap_static') }}
),

teams as (
    select snapshot_date, source_file, unnest(json_extract(payload, '$.teams[*]')) as t
    from source
)

select
    snapshot_date,
    (t ->> 'id')::integer as team_id,
    (t ->> 'code')::integer as team_code,
    t ->> 'name' as team_name,
    t ->> 'short_name' as short_name,
    (t ->> 'strength')::integer as strength,
    (t ->> 'strength_overall_home')::integer as strength_overall_home,
    (t ->> 'strength_overall_away')::integer as strength_overall_away,
    (t ->> 'strength_attack_home')::integer as strength_attack_home,
    (t ->> 'strength_attack_away')::integer as strength_attack_away,
    (t ->> 'strength_defence_home')::integer as strength_defence_home,
    (t ->> 'strength_defence_away')::integer as strength_defence_away,
    source_file
from teams
