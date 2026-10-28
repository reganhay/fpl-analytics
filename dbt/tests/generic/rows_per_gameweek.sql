-- Fails for any gameweek_id whose row count is not exactly `expected`,
-- e.g. 15 picks per gameweek.
{% test rows_per_gameweek(model, expected) %}

select gameweek_id, count(*) as row_count
from {{ model }}
group by gameweek_id
having count(*) != {{ expected }}

{% endtest %}
