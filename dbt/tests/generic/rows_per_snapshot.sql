-- Fails for any snapshot_date whose row count is not exactly `expected`,
-- e.g. 20 teams per daily snapshot. Catches truncated or partial pulls.
{% test rows_per_snapshot(model, expected) %}

select snapshot_date, count(*) as row_count
from {{ model }}
group by snapshot_date
having count(*) != {{ expected }}

{% endtest %}
