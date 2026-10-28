-- Schema-drift warning for a raw source table. Compares the JSON field names found at
-- `path` in the latest snapshot with the snapshot before it, and returns any field that
-- was added or removed. With only one snapshot there is nothing to compare, so it passes.
{% test json_key_drift(model, path) %}
{{ config(severity = 'warn') }}

with dates as (
    select distinct snapshot_date
    from {{ model }}
    order by snapshot_date desc
    limit 2
),

items as (
    select snapshot_date, unnest(json_extract(payload, '{{ path }}')) as item
    from {{ model }}
    where snapshot_date in (select snapshot_date from dates)
),

keys as (
    select distinct snapshot_date, unnest(json_keys(item)) as field_name
    from items
),

latest as (
    select field_name from keys where snapshot_date = (select max(snapshot_date) from dates)
),

previous as (
    select field_name from keys where snapshot_date = (select min(snapshot_date) from dates)
)

select 'added' as change, field_name
from (select field_name from latest except select field_name from previous)
union all
select 'removed' as change, field_name
from (select field_name from previous except select field_name from latest)

{% endtest %}
