-- One row per fixture per daily snapshot, from fixtures/.
-- Kickoff times, scores and difficulty can all change, so every snapshot is kept;
-- pick the latest snapshot per fixture downstream when you only need the current state.
-- gameweek_id is null for postponed fixtures that have not been rescheduled yet.

with source as (
    select snapshot_date, source_file, payload
    from {{ source('fpl_raw', 'fixtures') }}
),

fixtures as (
    select snapshot_date, source_file, unnest(json_extract(payload, '$[*]')) as f
    from source
)

select
    snapshot_date,
    (f ->> 'id')::integer as fixture_id,
    (f ->> 'code')::integer as fixture_code,
    (f ->> 'event')::integer as gameweek_id,
    (f ->> 'kickoff_time')::timestamptz as kickoff_time,
    (f ->> 'team_h')::integer as home_team_id,
    (f ->> 'team_a')::integer as away_team_id,
    (f ->> 'team_h_score')::integer as home_score,
    (f ->> 'team_a_score')::integer as away_score,
    (f ->> 'team_h_difficulty')::integer as home_difficulty,
    (f ->> 'team_a_difficulty')::integer as away_difficulty,
    (f ->> 'started')::boolean as is_started,
    (f ->> 'finished_provisional')::boolean as is_finished_provisional,
    (f ->> 'finished')::boolean as is_finished,
    (f ->> 'minutes')::integer as minutes_played,
    source_file
from fixtures
