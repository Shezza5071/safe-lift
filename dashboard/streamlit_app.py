"""Safe Lift trainer dashboard (Streamlit in Snowflake). Reads H4H.APP.EVENTS; no outside calls."""
import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Safe Lift trainer view", layout="wide")
s = get_active_session()


def q(sql):
    return s.sql(sql).to_pandas()


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

st.subheader("Recent sessions")
st.dataframe(latest, use_container_width=True)
if live:
    import time
    time.sleep(5)
    st.rerun()
