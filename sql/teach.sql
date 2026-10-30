-- Gemma teaches Snowflake ML: compare four raters on the same held-out, human-labelled readings.
-- Needs H4H.APP.GEMMA_LABELS (teach.py). Run: .venv/bin/python sql/run.py sql/teach.sql
-- Test set = last 40% (by time) of the newest labelled session. Everything else labelled = training.

create or replace table H4H.APP.LIFT_SPLIT as
with newest as (
    select session_id from H4H.APP.EVENTS where label is not null
    group by 1 order by max(ts) desc limit 1
), f as (
    select lf.*, g.gemma_label, e.reba_band,
           percent_rank() over (partition by lf.session_id order by lf.ts) as pr
    from H4H.APP.LIFT_FEATURES lf
    join H4H.APP.EVENTS e on e.session_id = lf.session_id and e.ts = lf.ts
    left join H4H.APP.GEMMA_LABELS g on g.session_id = lf.session_id and g.ts = lf.ts
    where lf.label is not null
)
select f.*, (f.session_id = (select session_id from newest) and f.pr >= 0.6) as is_test from f;

-- v1: human labels as given. v2: drop training readings where Gemma disagrees with the human (label cleaning).
create or replace view H4H.APP.LIFT_TRAIN_V1 as
select trunk_deg, twist_deg, knee_deg, d_trunk, d_twist, max_trunk_3, label
from H4H.APP.LIFT_SPLIT where not is_test;

create or replace view H4H.APP.LIFT_TRAIN_V2 as
select trunk_deg, twist_deg, knee_deg, d_trunk, d_twist, max_trunk_3, label
from H4H.APP.LIFT_SPLIT where not is_test and (gemma_label is null or gemma_label = label);

create or replace SNOWFLAKE.ML.CLASSIFICATION H4H.APP.LIFT_MODEL_V1(
    INPUT_DATA => SYSTEM$REFERENCE('VIEW', 'H4H.APP.LIFT_TRAIN_V1'), TARGET_COLNAME => 'LABEL');

create or replace SNOWFLAKE.ML.CLASSIFICATION H4H.APP.LIFT_MODEL_V2(
    INPUT_DATA => SYSTEM$REFERENCE('VIEW', 'H4H.APP.LIFT_TRAIN_V2'), TARGET_COLNAME => 'LABEL');

create or replace table H4H.APP.MODEL_COMPARE as
with t as (
    select label,
           iff(reba_band = 'red', 'bad', 'good') as reba_rule,
           gemma_label as gemma_alone,
           H4H.APP.LIFT_MODEL_V1!PREDICT(INPUT_DATA => object_construct('TRUNK_DEG', trunk_deg,
               'TWIST_DEG', twist_deg, 'KNEE_DEG', knee_deg, 'D_TRUNK', d_trunk, 'D_TWIST', d_twist,
               'MAX_TRUNK_3', max_trunk_3)):class::string as ml_v1,
           H4H.APP.LIFT_MODEL_V2!PREDICT(INPUT_DATA => object_construct('TRUNK_DEG', trunk_deg,
               'TWIST_DEG', twist_deg, 'KNEE_DEG', knee_deg, 'D_TRUNK', d_trunk, 'D_TWIST', d_twist,
               'MAX_TRUNK_3', max_trunk_3)):class::string as ml_v2
    from H4H.APP.LIFT_SPLIT where is_test
), long as (
    select label, 'REBA angle rule' as rater, 1 as ord, reba_rule as pred from t
    union all select label, 'Gemma alone (skeleton only)', 2, gemma_alone from t where gemma_alone is not null
    union all select label, 'Snowflake ML v1 (human labels)', 3, ml_v1 from t
    union all select label, 'Snowflake ML v2 (human labels cleaned by Gemma)', 4, ml_v2 from t
)
select rater, ord, count(*) as test_readings,
       round(100 * avg(iff(pred = label, 1, 0))) as accuracy_pct,
       round(100 * sum(iff(pred = 'bad' and label = 'bad', 1, 0)) / nullif(sum(iff(label = 'bad', 1, 0)), 0)) as bad_caught_pct,
       round(100 * sum(iff(pred = 'bad' and label = 'bad', 1, 0)) / nullif(sum(iff(pred = 'bad', 1, 0)), 0)) as flags_correct_pct,
       (select count(*) from H4H.APP.LIFT_TRAIN_V1) as v1_train_rows,
       (select count(*) from H4H.APP.LIFT_TRAIN_V2) as v2_train_rows
from long group by rater, ord order by ord;

-- How often Gemma agrees with the human labeller (all readings it rated).
create or replace table H4H.APP.GEMMA_AGREEMENT as
select e.label as human, g.gemma_label as gemma, count(*) as n
from H4H.APP.GEMMA_LABELS g
join H4H.APP.EVENTS e on e.session_id = g.session_id and e.ts = g.ts
where e.label is not null group by 1, 2;
