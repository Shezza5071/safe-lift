-- Train and evaluate the lift risk model (map contract 3). Rerun after each labelling round:
--   .venv/bin/python sql/run.py sql/train.sql

-- Training data: labelled readings, minus those where Gemma's second-rater label disagrees with the human
-- (won 74% vs 52% held-out accuracy in sql/teach.sql). Readings Gemma has not rated are kept.
create or replace view H4H.APP.LIFT_TRAIN as
select f.trunk_deg, f.twist_deg, f.knee_deg, f.d_trunk, f.d_twist, f.max_trunk_3, f.label
from H4H.APP.LIFT_FEATURES f
left join H4H.APP.GEMMA_LABELS g on g.session_id = f.session_id and g.ts = f.ts
where f.label is not null and (g.gemma_label is null or g.gemma_label = f.label);

-- Snowflake ML classifier; 'evaluate' holds out part of the data and reports metrics on it.
create or replace SNOWFLAKE.ML.CLASSIFICATION H4H.APP.LIFT_RISK_MODEL(
    INPUT_DATA => SYSTEM$REFERENCE('VIEW', 'H4H.APP.LIFT_TRAIN'),
    TARGET_COLNAME => 'LABEL',
    CONFIG_OBJECT => {'evaluate': TRUE}
);

-- Score every reading (labelled or not) and compare with the REBA rule.
create or replace table H4H.APP.MODEL_EVAL as
select f.session_id, f.ts, e.task, e.reba_band, f.label,
       p:class::string as predicted,
       round(p:probability:bad::float, 3) as prob_bad,
       e.reba_band = 'red' as rule_bad,
       p:class::string = 'bad' as ml_bad
from (
    select *, H4H.APP.LIFT_RISK_MODEL!PREDICT(INPUT_DATA => object_construct(
        'TRUNK_DEG', trunk_deg, 'TWIST_DEG', twist_deg, 'KNEE_DEG', knee_deg,
        'D_TRUNK', d_trunk, 'D_TWIST', d_twist, 'MAX_TRUNK_3', max_trunk_3)) as p
    from H4H.APP.LIFT_FEATURES
) f
join H4H.APP.EVENTS e on e.session_id = f.session_id and e.ts = f.ts;
