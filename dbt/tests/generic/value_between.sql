-- Fails for rows where the column falls outside [min_value, max_value]. Nulls pass;
-- use not_null alongside it when the column must be filled.
{% test value_between(model, column_name, min_value, max_value) %}

select {{ column_name }}
from {{ model }}
where {{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }}

{% endtest %}
