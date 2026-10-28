-- One row per player per daily snapshot, from bootstrap-static.
-- Prices arrive in tenths of a million (now_cost 62 = £6.2m) and are converted here, once.
-- Several numbers arrive as text ("6.3") and are cast to decimals.

with source as (
    select snapshot_date, source_file, payload
    from {{ source('fpl_raw', 'bootstrap_static') }}
),

players as (
    select snapshot_date, source_file, unnest(json_extract(payload, '$.elements[*]')) as p
    from source
),

positions as (
    select
        snapshot_date,
        (t ->> 'id')::integer as element_type,
        t ->> 'singular_name_short' as position
    from (
        select snapshot_date, unnest(json_extract(payload, '$.element_types[*]')) as t
        from source
    )
)

select
    players.snapshot_date,
    (p ->> 'id')::integer as player_id,
    (p ->> 'code')::integer as player_code,
    p ->> 'web_name' as web_name,
    p ->> 'first_name' as first_name,
    p ->> 'second_name' as second_name,
    positions.position,
    (p ->> 'team')::integer as team_id,

    -- price and ownership
    ((p ->> 'now_cost')::integer / 10)::decimal(5, 1) as price_gbp,
    ((p ->> 'cost_change_event')::integer / 10)::decimal(5, 1) as price_change_gameweek_gbp,
    ((p ->> 'cost_change_start')::integer / 10)::decimal(5, 1) as price_change_season_gbp,
    (p ->> 'price_change_percent')::decimal(6, 1) as price_change_percent,
    (p ->> 'selected_by_percent')::decimal(5, 1) as selected_pct,
    (p ->> 'transfers_in')::integer as transfers_in,
    (p ->> 'transfers_out')::integer as transfers_out,
    (p ->> 'transfers_in_event')::integer as transfers_in_event,
    (p ->> 'transfers_out_event')::integer as transfers_out_event,

    -- availability
    p ->> 'status' as status,
    (p ->> 'chance_of_playing_this_round')::integer as chance_of_playing_this_round,
    (p ->> 'chance_of_playing_next_round')::integer as chance_of_playing_next_round,
    nullif(p ->> 'news', '') as news,
    (p ->> 'news_added')::timestamptz as news_added_at,

    -- season-to-date performance
    (p ->> 'total_points')::integer as total_points,
    (p ->> 'event_points')::integer as gameweek_points,
    (p ->> 'form')::decimal(4, 1) as form,
    (p ->> 'points_per_game')::decimal(4, 1) as points_per_game,
    (p ->> 'ep_next')::decimal(4, 1) as expected_points_next,
    (p ->> 'minutes')::integer as minutes,
    (p ->> 'starts')::integer as starts,
    (p ->> 'goals_scored')::integer as goals,
    (p ->> 'assists')::integer as assists,
    (p ->> 'clean_sheets')::integer as clean_sheets,
    (p ->> 'goals_conceded')::integer as goals_conceded,
    (p ->> 'saves')::integer as saves,
    (p ->> 'bonus')::integer as bonus,
    (p ->> 'bps')::integer as bps,
    (p ->> 'defensive_contribution')::integer as defensive_contribution,
    (p ->> 'expected_goals')::decimal(6, 2) as expected_goals,
    (p ->> 'expected_assists')::decimal(6, 2) as expected_assists,
    (p ->> 'expected_goal_involvements')::decimal(6, 2) as expected_goal_involvements,
    (p ->> 'expected_goals_conceded')::decimal(6, 2) as expected_goals_conceded,
    (p ->> 'ict_index')::decimal(6, 1) as ict_index,

    players.source_file
from players
left join positions
    on players.snapshot_date = positions.snapshot_date
    and (p ->> 'element_type')::integer = positions.element_type
