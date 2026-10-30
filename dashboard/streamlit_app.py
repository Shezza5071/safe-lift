"""Safe Lift trainer dashboard (Streamlit in Snowflake). Reads H4H.APP tables and H4H.HEALTH open data; no outside calls."""
import pandas as pd
import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Safe Lift trainer view", layout="wide")
s = get_active_session()


def q(sql):
    return s.sql(sql).to_pandas()


def q_or_none(sql, what):
    """For tiles whose table may not exist yet (sql/train.sql, sql/teach.sql): show why, keep the page running."""
    try:
        return q(sql)
    except Exception as e:
        st.caption(f"{what} unavailable: {str(e).splitlines()[0][:160]}")
        return None


CONTEXT = "Context (AIHW GEN, 30 June 2025)"


now = q("select convert_timezone('Australia/Adelaide', current_timestamp())::timestamp_ntz as n")["N"][0]
last = q("select max(ts) as t from H4H.APP.EVENTS")["T"][0]
live = last is not None and (now - last).total_seconds() < 15

st.title("Safe Lift: trainer view")
st.caption(f"Adelaide time {now:%H:%M:%S} · {'🟢 LIVE' if live else '⚪ idle'} · training-room mode, no video saved")

latest = q("""select session_id, task, staff_code, count(*) readings, sum(iff(alarm,1,0)) alarms,
  round(100*avg(iff(reba_band='green',1,0))) pct_green,
  round(100*avg(iff(reba_band='amber',1,0))) pct_amber,
  round(100*avg(iff(reba_band='red',1,0))) pct_red, max(ts) last_seen
  from H4H.APP.EVENTS group by 1,2,3 order by last_seen desc limit 10""")

if latest.empty:
    st.info("No readings yet. Start a session on the laptop.")
    st.stop()

cur = latest.iloc[0]
c = st.columns(4)
c[0].metric("Current session", cur["SESSION_ID"], cur["TASK"])
c[1].metric("Red alarms", int(cur["ALARMS"]))
c[2].metric("% time green", f"{cur['PCT_GREEN']:.0f}%")
c[3].metric("% time red", f"{cur['PCT_RED']:.0f}%")

st.subheader("Trunk angle, current session (bands, not exact degrees: ±5 to 10°)")
trace = q(f"select ts, trunk_deg, twist_deg from H4H.APP.EVENTS where session_id='{cur['SESSION_ID']}' order by ts")
st.line_chart(trace, x="TS", y=["TRUNK_DEG", "TWIST_DEG"])

deb = q("""select session_id, ts, language, debrief, citations, source from H4H.APP.DEBRIEFS
  order by ts desc limit 1""")
if not deb.empty:
    d = deb.iloc[0]
    st.subheader(f"Gemma debrief ({d['LANGUAGE']}, session {d['SESSION_ID']})"
                 + (" · cached" if d["SOURCE"] == "cache" else ""))
    st.info(d["DEBRIEF"])
    st.caption("Sources (Cortex Search): " + "; ".join(
        f"[{i + 1}] {c}" for i, c in enumerate(__import__("json").loads(d["CITATIONS"]))))

lab = q("""select answer, count(*) n from H4H.APP.ALARM_LABELS group by 1 order by 2 desc""")
if not lab.empty:
    st.subheader("Why red alarms happened (trainee answers to Gemma)")
    st.bar_chart(lab, x="ANSWER", y="N")

st.subheader("Alarms by task (look at the task and plan, not the person)")
st.bar_chart(q("""select task, sum(iff(alarm,1,0)) alarms, count(*) readings
  from H4H.APP.EVENTS group by 1 order by 2 desc"""), x="TASK", y="ALARMS")

st.subheader("Snowflake ML: does the learned risk flag agree with the REBA rule?")
st.caption("The ML flag is learned from team-labelled lifts (few people, staged lifts) and is shown as a badge only; "
           "the beep always follows the REBA angle rule.")
# MODEL_EVAL is a snapshot from the last sql/train.sql run, so "latest" means the newest session it scored.
agree = q_or_none("""select session_id, count(*) n, round(100*avg(iff(rule_bad = ml_bad, 1, 0))) pct_agree,
  sum(iff(ml_bad, 1, 0)) ml_flags, sum(iff(rule_bad, 1, 0)) rule_flags
  from H4H.APP.MODEL_EVAL group by 1 order by max(ts) desc limit 1""", "ML agreement")
allr = q_or_none("""select count(*) n, round(100*avg(iff(rule_bad = ml_bad, 1, 0))) pct_agree,
  from H4H.APP.MODEL_EVAL""", "ML agreement")
if allr is not None and not allr["N"][0]:
    st.info("Model not trained yet (run sql/train.sql).")
elif allr is not None:
    a = st.columns(2)
    if agree is not None and not agree.empty and pd.notna(agree["PCT_AGREE"][0]):
        a[0].metric(f"ML vs REBA agreement, latest scored session ({agree['SESSION_ID'][0]})",
                    f"{agree['PCT_AGREE'][0]:.0f}%",
                    f"ML flags {int(agree['ML_FLAGS'][0])} · REBA red {int(agree['RULE_FLAGS'][0])}", delta_color="off")
    a[1].metric("ML vs REBA agreement, all readings", f"{allr['PCT_AGREE'][0]:.0f}%" if pd.notna(allr["PCT_AGREE"][0]) else "n/a", f"{int(allr['N'][0])} readings",
                delta_color="off")

compare = q_or_none("""select rater, test_readings, accuracy_pct, bad_caught_pct, flags_correct_pct
  from H4H.APP.MODEL_COMPARE order by ord""", "Model comparison")
if compare is not None and not compare.empty:
    st.markdown("**Model accuracy on held-out, human-labelled readings** (Gemma teaches Snowflake ML)")
    st.dataframe(compare.rename(columns={"RATER": "Rater", "TEST_READINGS": "Test readings",
                                         "ACCURACY_PCT": "Accuracy %", "BAD_CAUGHT_PCT": "Bad lifts caught %",
                                         "FLAGS_CORRECT_PCT": "Flags correct %"}),
                 use_container_width=True)
    st.caption(f"Small test set ({int(compare['TEST_READINGS'].max())} readings from staged lifts by a few teammates): "
               "indicative only, not a validated safety measure.")

st.subheader("Why it matters in South Australia")
ctx = q_or_none("""select
  (select coalesce(sum(total), 0) from H4H.HEALTH.A2_GEN_DATA_PEOPLE_USING_AGED_CARE_BY_REGION_30_JUNE_2025_4_RESIDENTIAL_CARE_SERVICE_LOCATION_TABLE_4_4_PHN
   where phn_code in ('PHN401','PHN402')) residential,
  (select coalesce(sum(total), 0) from H4H.HEALTH.A2_GEN_DATA_PEOPLE_USING_AGED_CARE_BY_REGION_30_JUNE_2025_2_HOME_CARE_RECIPIENT_LOCATION_TABLE_2_4_PHN
   where phn_2017_code in ('PHN401','PHN402')) home_care""", "Aged care context")  # PHN401 Adelaide + PHN402 Country SA
if ctx is not None:
    i = st.columns(2)
    i[0].metric("Living in residential aged care, SA", f"{int(ctx['RESIDENTIAL'][0]):,}",
                CONTEXT, delta_color="off")
    i[0].caption("17,358 people were living in residential aged care in South Australia at 30 June 2025: "
                 "residents who depend on safe transfers every day.")
    i[1].metric("Receiving home care packages, SA", f"{int(ctx['HOME_CARE'][0]):,}",
                CONTEXT, delta_color="off")
    i[1].caption("28,006 South Australians were receiving home care packages at 30 June 2025.")
    st.caption("Australian Institute of Health and Welfare, *GEN data: People using aged care by region data tables* "
               "(released 12 Feb 2026), 30 June 2025, residential care by service location, Table 4.4 (PHN); "
               "home care by recipient location, Table 2.4 (PHN). Via H4H Snowflake (`H4H.HEALTH`). "
               "Context only, not Safe Lift data; the two counts are not added together.")

st.subheader("Recent sessions")
st.dataframe(latest, use_container_width=True)
if live:
    import time
    time.sleep(5)
    st.rerun()
