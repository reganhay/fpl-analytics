-- One row per player per fixture played this season, from element-summary/{id}/ history.
-- price_gbp and selected are the player's price and ownership at that match.
-- If a player's history was saved more than once, the latest file wins.

with source as (
    select snapshot_date, source_file, payload
    from {{ source('fpl_raw', 'element_summary') }}
),

matches as (
    select snapshot_date, source_file, unnest(json_extract(payload, '$.history[*]')) as h
    from source
)

select
    (h ->> 'element')::integer as player_id,
    (h ->> 'fixture')::integer as fixture_id,
    (h ->> 'round')::integer as gameweek_id,
    (h ->> 'opponent_team')::integer as opponent_team_id,
    (h ->> 'was_home')::boolean as was_home,
    (h ->> 'kickoff_time')::timestamptz as kickoff_time,
    (h ->> 'minutes')::integer as minutes,
    (h ->> 'starts')::integer as starts,
    (h ->> 'total_points')::integer as total_points,
    (h ->> 'goals_scored')::integer as goals,
    (h ->> 'assists')::integer as assists,
    (h ->> 'clean_sheets')::integer as clean_sheets,
    (h ->> 'goals_conceded')::integer as goals_conceded,
    (h ->> 'own_goals')::integer as own_goals,
    (h ->> 'penalties_saved')::integer as penalties_saved,
    (h ->> 'penalties_missed')::integer as penalties_missed,
    (h ->> 'yellow_cards')::integer as yellow_cards,
    (h ->> 'red_cards')::integer as red_cards,
    (h ->> 'saves')::integer as saves,
    (h ->> 'bonus')::integer as bonus,
    (h ->> 'bps')::integer as bps,
    (h ->> 'defensive_contribution')::integer as defensive_contribution,
    (h ->> 'expected_goals')::decimal(6, 2) as expected_goals,
    (h ->> 'expected_assists')::decimal(6, 2) as expected_assists,
    (h ->> 'expected_goal_involvements')::decimal(6, 2) as expected_goal_involvements,
    (h ->> 'expected_goals_conceded')::decimal(6, 2) as expected_goals_conceded,
    (h ->> 'ict_index')::decimal(6, 1) as ict_index,
    ((h ->> 'value')::integer / 10)::decimal(5, 1) as price_gbp,
    (h ->> 'selected')::integer as selected,
    (h ->> 'transfers_in')::integer as transfers_in,
    (h ->> 'transfers_out')::integer as transfers_out,
    (h ->> 'transfers_balance')::integer as transfers_balance,
    snapshot_date,
    source_file
from matches
qualify row_number() over (partition by player_id, fixture_id order by snapshot_date desc) = 1
