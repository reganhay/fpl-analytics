-- Fails for every combination of the given columns that appears more than once.
-- This is how a table's grain is enforced, e.g. one row per (player_id, snapshot_date).
{% test unique_combination(model, columns) %}

select {{ columns | join(', ') }}, count(*) as row_count
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1

{% endtest %}
