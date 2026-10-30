-- Feature view for the lift risk model (map contract 2). One row per 2 s reading in H4H.APP.EVENTS.
-- d_* = change since the previous reading in the same session (0 for the first);
-- max_trunk_3 = highest trunk angle over this and the previous 2 readings.
create or replace view H4H.APP.LIFT_FEATURES as
select
    session_id,
    ts,
    trunk_deg,
    twist_deg,
    knee_deg,
    round(coalesce(trunk_deg - lag(trunk_deg) over (partition by session_id order by ts), 0), 1) as d_trunk,
    round(coalesce(twist_deg - lag(twist_deg) over (partition by session_id order by ts), 0), 1) as d_twist,
    max(trunk_deg) over (partition by session_id order by ts rows between 2 preceding and current row) as max_trunk_3,
    label
from H4H.APP.EVENTS;
