-- One row per player per final gameweek, from event/{gw}/live/.
-- Grain is the gameweek, not the fixture: in a double gameweek these stats are the sum of
-- both matches. fixture_count says how many matches the row covers.
-- Each gameweek is normally saved once; if it was saved again, the latest file wins.

with source as (
    select snapshot_date, entity_key, source_file, payload
    from {{ source('fpl_raw', 'event_live') }}
),

players as (
    select
        snapshot_date,
        source_file,
        substr(entity_key, 3)::integer as gameweek_id,
        unnest(json_extract(payload, '$.elements[*]')) as p
    from source
)

select
    gameweek_id,
    (p ->> 'id')::integer as player_id,
    json_array_length(p -> 'explain') as fixture_count,
    (p ->> '$.stats.minutes')::integer as minutes,
    (p ->> '$.stats.total_points')::integer as total_points,
    (p ->> '$.stats.goals_scored')::integer as goals,
    (p ->> '$.stats.assists')::integer as assists,
    (p ->> '$.stats.clean_sheets')::integer as clean_sheets,
    (p ->> '$.stats.goals_conceded')::integer as goals_conceded,
    (p ->> '$.stats.saves')::integer as saves,
    (p ->> '$.stats.yellow_cards')::integer as yellow_cards,
    (p ->> '$.stats.red_cards')::integer as red_cards,
    (p ->> '$.stats.bonus')::integer as bonus,
    (p ->> '$.stats.bps')::integer as bps,
    (p ->> '$.stats.defensive_contribution')::integer as defensive_contribution,
    (p ->> '$.stats.starts')::integer as starts,
    (p ->> '$.stats.expected_goals')::decimal(6, 2) as expected_goals,
    (p ->> '$.stats.expected_assists')::decimal(6, 2) as expected_assists,
    (p ->> '$.stats.expected_goal_involvements')::decimal(6, 2) as expected_goal_involvements,
    (p ->> '$.stats.expected_goals_conceded')::decimal(6, 2) as expected_goals_conceded,
    (p ->> '$.stats.in_dreamteam')::boolean as in_dreamteam,
    snapshot_date,
    source_file
from players
qualify row_number() over (partition by gameweek_id, player_id order by snapshot_date desc) = 1
