"""Safe Lift trainer console (Streamlit in Snowflake).

Reads H4H.APP tables, H4H.HEALTH open data, and two Snowflake Marketplace Cortex Search services
(PubMed Biomedical Research Corpus, Clinical Trials Research Database). No outside calls.
"""
import json

import altair as alt
import pandas as pd
import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Safe Lift · trainer console", page_icon="🦺", layout="wide")
s = get_active_session()

GREEN, AMBER, RED, VIOLET, INK = "#22c55e", "#f59e0b", "#ef4444", "#a855f7", "#e2e8f0"
CONTEXT = "Context (AIHW GEN, 30 June 2025)"

st.markdown(f"""<style>
.stApp {{ background: radial-gradient(1200px 600px at 10% -10%, #1e1b4b 0%, #0b1020 45%, #070a14 100%); color: {INK}; }}
.block-container {{ padding-top: 1.6rem; max-width: 1400px; }}
h1, h2, h3, h4, p, label, span, div {{ color: {INK}; }}
.hero {{ display:flex; justify-content:space-between; align-items:center; padding: 22px 28px; border-radius: 22px;
  background: linear-gradient(135deg, rgba(99,102,241,.25), rgba(168,85,247,.18) 50%, rgba(34,197,94,.12));
  border: 1px solid rgba(148,163,184,.18); box-shadow: 0 20px 60px rgba(0,0,0,.35); margin-bottom: 18px; }}
.hero h1 {{ margin:0; font-size: 2.3rem; letter-spacing: -0.02em; }}
.hero .tag {{ color:#a5b4fc; font-size: 1.02rem; margin-top: 4px; }}
.pill {{ padding: 8px 16px; border-radius: 999px; font-weight: 700; font-size: .95rem; display:inline-block; }}
.live {{ background: rgba(34,197,94,.15); color:{GREEN}; border:1px solid rgba(34,197,94,.5); animation: pulse 1.6s infinite; }}
.idle {{ background: rgba(148,163,184,.12); color:#94a3b8; border:1px solid rgba(148,163,184,.35); }}
@keyframes pulse {{ 0%{{box-shadow:0 0 0 0 rgba(34,197,94,.55)}} 70%{{box-shadow:0 0 0 12px rgba(34,197,94,0)}} 100%{{box-shadow:0 0 0 0 rgba(34,197,94,0)}} }}
.card {{ padding: 18px 20px; border-radius: 18px; background: rgba(15,23,42,.72); border: 1px solid rgba(148,163,184,.16);
  box-shadow: 0 10px 30px rgba(0,0,0,.25); height: 100%; }}
.card .k {{ color:#94a3b8; font-size:.82rem; text-transform: uppercase; letter-spacing:.08em; }}
.card .v {{ font-size: 2.2rem; font-weight: 800; margin-top: 4px; }}
.card .s {{ color:#94a3b8; font-size:.85rem; margin-top: 2px; }}
.gemma {{ padding: 20px 22px; border-radius: 18px; background: linear-gradient(135deg, rgba(168,85,247,.16), rgba(15,23,42,.8));
  border: 1px solid rgba(168,85,247,.35); font-size: 1.05rem; line-height: 1.6; }}
.paper {{ padding: 14px 16px; border-radius: 14px; background: rgba(15,23,42,.7); border: 1px solid rgba(148,163,184,.14);
  margin-bottom: 10px; }}
.paper a {{ color:#a5b4fc; text-decoration:none; font-weight:600; }}
.muted {{ color:#94a3b8; font-size:.85rem; }}
.stTabs [data-baseweb="tab"] {{ font-size: 1.02rem; font-weight: 600; }}
div[data-testid="stDataFrame"] {{ border-radius: 14px; overflow: hidden; }}
</style>""", unsafe_allow_html=True)


def q(sql):
    return s.sql(sql).to_pandas()


def q_or_none(sql):
    try:
        return q(sql)
    except Exception:
        return None


def card(col, k, v, sub="", colour=INK):
    col.markdown(f'<div class="card"><div class="k">{k}</div><div class="v" style="color:{colour}">{v}</div>'
                 f'<div class="s">{sub}</div></div>', unsafe_allow_html=True)


now = q("select convert_timezone('Australia/Adelaide', current_timestamp())::timestamp_ntz as n")["N"][0]
last = q("select max(ts) as t from H4H.APP.EVENTS")["T"][0]
live = last is not None and (now - last).total_seconds() < 15

st.markdown(f"""<div class="hero"><div><h1>🦺 Safe Lift</h1>
<div class="tag">MediaPipe is the eyes · Gemma is the coach · Snowflake is the memory</div></div>
<div style="text-align:right"><span class="pill {'live' if live else 'idle'}">{'● LIVE' if live else '○ idle'}</span>
<div class="muted" style="margin-top:8px">Adelaide {now:%H:%M:%S} · training-room mode · no video saved</div></div></div>""",
            unsafe_allow_html=True)

latest = q("""select session_id, task, staff_code, count(*) readings, sum(iff(alarm,1,0)) alarms,
  round(100*avg(iff(reba_band='green',1,0))) pct_green, round(100*avg(iff(reba_band='amber',1,0))) pct_amber,
  round(100*avg(iff(reba_band='red',1,0))) pct_red, max(ts) last_seen
  from H4H.APP.EVENTS group by 1,2,3 order by last_seen desc limit 10""")
if latest.empty:
    st.info("No readings yet. Start a session on the laptop.")
    st.stop()
cur = latest.iloc[0]

tab_live, tab_ml, tab_ev, tab_impact = st.tabs(
    ["🎥  Live session", "🧠  Gemma × Snowflake ML", "📚  Evidence", "🌏  Why it matters"])

# ---------------------------------------------------------------- live session
with tab_live:
    c = st.columns(4)
    card(c[0], "Session", cur["SESSION_ID"], cur["TASK"].replace("_", " "))
    card(c[1], "Red alarms", int(cur["ALARMS"]), "REBA rule, held 2 s", RED if cur["ALARMS"] else GREEN)
    card(c[2], "Time in safe band", f"{cur['PCT_GREEN']:.0f}%", "green: trunk ≤ 20°", GREEN)
    card(c[3], "Time in red band", f"{cur['PCT_RED']:.0f}%", "> 60°, or > 20° with twist", RED)

    st.markdown("#### Trunk angle, this session")
    trace = q(f"""select ts, trunk_deg, twist_deg, reba_band from H4H.APP.EVENTS
                  where session_id='{cur['SESSION_ID']}' order by ts""")
    if not trace.empty:
        t0, t1 = trace["TS"].min(), trace["TS"].max()
        zones = pd.DataFrame({"y0": [0, 20, 60], "y1": [20, 60, 120], "zone": ["safe", "careful", "risky"],
                              "t0": [t0] * 3, "t1": [t1] * 3})
        bands = alt.Chart(zones).mark_rect(opacity=0.13).encode(
            x="t0:T", x2="t1:T", y="y0:Q", y2="y1:Q",
            color=alt.Color("zone:N", scale=alt.Scale(domain=["safe", "careful", "risky"], range=[GREEN, AMBER, RED]),
                            legend=None))
        line = alt.Chart(trace).mark_line(strokeWidth=3, color="#c7d2fe", interpolate="monotone").encode(
            x=alt.X("TS:T", title=None), y=alt.Y("TRUNK_DEG:Q", title="trunk bend (°)", scale=alt.Scale(domain=[0, 120])))
        dots = alt.Chart(trace).mark_circle(size=70).encode(
            x="TS:T", y="TRUNK_DEG:Q",
            color=alt.Color("REBA_BAND:N", scale=alt.Scale(domain=["green", "amber", "red"], range=[GREEN, AMBER, RED]),
                            legend=None),
            tooltip=[alt.Tooltip("TS:T", format="%H:%M:%S"), "TRUNK_DEG", "TWIST_DEG", "REBA_BAND"])
        st.altair_chart((bands + line + dots).properties(height=320).configure_view(strokeWidth=0)
                        .configure_axis(labelColor="#94a3b8", titleColor="#94a3b8", gridColor="#1e293b"),
                        use_container_width=True)
        st.markdown('<div class="muted">Bands, not exact degrees: single-camera pose is ±5 to 10°.</div>',
                    unsafe_allow_html=True)

    deb = q("select session_id, language, debrief, citations, source from H4H.APP.DEBRIEFS order by ts desc limit 1")
    left, right = st.columns([3, 2])
    with left:
        if not deb.empty:
            d = deb.iloc[0]
            st.markdown(f"#### 💬 Gemma debrief · {d['LANGUAGE']}" + (" · cached" if d["SOURCE"] == "cache" else ""))
            st.markdown(f'<div class="gemma">{d["DEBRIEF"]}</div>', unsafe_allow_html=True)
            cites = "; ".join(f"[{i + 1}] {c}" for i, c in enumerate(json.loads(d["CITATIONS"])))
            st.markdown(f'<div class="muted" style="margin-top:8px">Grounded by Cortex Search: {cites}</div>',
                        unsafe_allow_html=True)
    with right:
        lab = q("select answer, count(*) n from H4H.APP.ALARM_LABELS group by 1 order by 2 desc")
        st.markdown("#### Why red alarms happened")
        if lab.empty:
            st.markdown('<div class="muted">Trainee answers to Gemma\'s question appear here.</div>',
                        unsafe_allow_html=True)
        else:
            st.altair_chart(alt.Chart(lab).mark_bar(cornerRadius=6, color=VIOLET).encode(
                x=alt.X("N:Q", title=None), y=alt.Y("ANSWER:N", sort="-x", title=None))
                .properties(height=220).configure_axis(labelColor="#cbd5e1", gridColor="#1e293b")
                .configure_view(strokeWidth=0), use_container_width=True)
        st.markdown("#### Alarms by task")
        st.markdown('<div class="muted">Look at the task and the plan, not the person.</div>', unsafe_allow_html=True)
        st.altair_chart(alt.Chart(q("""select task, sum(iff(alarm,1,0)) alarms from H4H.APP.EVENTS group by 1""")
                                  ).mark_bar(cornerRadius=6, color=AMBER).encode(
            x=alt.X("ALARMS:Q", title=None), y=alt.Y("TASK:N", sort="-x", title=None))
            .properties(height=160).configure_axis(labelColor="#cbd5e1", gridColor="#1e293b")
            .configure_view(strokeWidth=0), use_container_width=True)

# ---------------------------------------------------------------- Gemma x Snowflake ML
with tab_ml:
    st.markdown("### Gemma teaches Snowflake ML")
    st.markdown('<div class="muted">Trainers label lifts good or bad. Gemma rates every reading\'s skeleton as a second '
                'rater; readings where they disagree are dropped. A Snowflake ML classifier learns from the cleaned '
                'labels and scores every reading live (the purple badge in the camera window).</div>',
                unsafe_allow_html=True)
    compare = q_or_none("""select rater, ord, test_readings, accuracy_pct, bad_caught_pct, flags_correct_pct,
                           v1_train_rows, v2_train_rows from H4H.APP.MODEL_COMPARE order by ord""")
    if compare is not None and not compare.empty:
        best = compare.sort_values("ACCURACY_PCT", ascending=False).iloc[0]
        c = st.columns(4)
        for col, (_, r) in zip(c, compare.iterrows()):
            win = r["RATER"] == best["RATER"]
            card(col, r["RATER"], f"{r['ACCURACY_PCT']:.0f}%",
                 f"accuracy · catches {r['BAD_CAUGHT_PCT']:.0f}% of bad lifts" if pd.notna(r["BAD_CAUGHT_PCT"]) else "accuracy",
                 VIOLET if win else INK)
        long = compare.melt(id_vars=["RATER", "ORD"], value_vars=["ACCURACY_PCT", "BAD_CAUGHT_PCT", "FLAGS_CORRECT_PCT"],
                            var_name="measure", value_name="pct")
        long["measure"] = long["measure"].map({"ACCURACY_PCT": "accuracy", "BAD_CAUGHT_PCT": "bad lifts caught",
                                               "FLAGS_CORRECT_PCT": "flags that were right"})
        st.altair_chart(alt.Chart(long).mark_bar(cornerRadius=6).encode(
            x=alt.X("pct:Q", title="%", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("RATER:N", sort=alt.SortField("ORD"), title=None),
            color=alt.Color("measure:N", scale=alt.Scale(range=[VIOLET, GREEN, "#38bdf8"]),
                            legend=alt.Legend(orient="top", labelColor="#cbd5e1", title=None)),
            yOffset="measure:N", tooltip=["RATER", "measure", "pct"])
            .properties(height=360).configure_axis(labelColor="#cbd5e1", titleColor="#94a3b8", gridColor="#1e293b")
            .configure_view(strokeWidth=0), use_container_width=True)
        st.markdown(f'<div class="muted">Held-out test: {int(compare["TEST_READINGS"].max())} human-labelled readings '
                    f'from staged lifts by a few teammates. v1 trained on {int(compare["V1_TRAIN_ROWS"].max())} readings, '
                    f'v2 on {int(compare["V2_TRAIN_ROWS"].max())} after Gemma\'s cleaning. Promising evidence, not a '
                    'validated safety measure. Gemma alone flags almost everything, so it is a teacher, not the alarm; '
                    'the beep always follows the REBA rule.</div>', unsafe_allow_html=True)
    else:
        st.info("Run sql/teach.sql to compare the raters.")

    agree = q_or_none("select human, gemma, n from H4H.APP.GEMMA_AGREEMENT")
    if agree is not None and not agree.empty:
        st.markdown("#### Human labeller vs Gemma")
        st.altair_chart(alt.Chart(agree).mark_rect(cornerRadius=8).encode(
            x=alt.X("GEMMA:N", title="Gemma said"), y=alt.Y("HUMAN:N", title="Human said"),
            color=alt.Color("N:Q", scale=alt.Scale(scheme="purples"), legend=None))
            .properties(height=200, width=360) + alt.Chart(agree).mark_text(fontSize=20, fontWeight="bold",
                                                                          color="white").encode(
            x="GEMMA:N", y="HUMAN:N", text="N:Q"), use_container_width=False)

# ---------------------------------------------------------------- evidence (Marketplace Cortex Search)
with tab_ev:
    st.markdown("### What the research says")
    st.markdown('<div class="muted">Live Cortex Search over two Snowflake Marketplace datasets: PubMed Biomedical '
                'Research Corpus and the Clinical Trials Research Database. Tips for trainers, with sources.</div>',
                unsafe_allow_html=True)
    topic = st.selectbox("Topic", ["patient handling interventions to prevent low back pain in nurses and aged care workers",
                                   "hoist and assistive device use for patient transfer",
                                   "manual handling training effectiveness for care workers",
                                   "reaching and twisting during bed to chair transfer"])

    @st.cache_data(ttl=900)
    def search(service, query, cols, limit):
        sql = ("select f.value v from table(flatten(parse_json(snowflake.cortex.search_preview("
               f"'{service}', $${json.dumps({'query': query, 'columns': cols, 'limit': limit})}$$)):results)) f")
        return [json.loads(r) for r in q(sql)["V"]]

    p_col, t_col = st.columns(2)
    with p_col:
        st.markdown("#### 📄 PubMed studies")
        try:
            seen = set()
            for h in search("PUBMED_BIOMEDICAL_RESEARCH_CORPUS.OA_COMM.PUBMED_CKE", topic,
                            ["TITLE", "CITATION", "ARTICLE_URL", "CHUNK"], 8):
                if h.get("TITLE") in seen or len(seen) == 4:
                    continue
                seen.add(h.get("TITLE"))
                st.markdown(f'<div class="paper"><a href="{h.get("ARTICLE_URL", "")}" target="_blank">{h.get("TITLE")}</a>'
                            f'<div class="muted">{(h.get("CITATION") or "")[:160]}</div>'
                            f'<div style="margin-top:6px;font-size:.9rem">“{(h.get("CHUNK") or "")[:260].strip()}…”</div></div>',
                            unsafe_allow_html=True)
        except Exception as e:
            st.caption(f"PubMed search unavailable: {str(e).splitlines()[0][:140]}")
    with t_col:
        st.markdown("#### 🧪 Clinical trials")
        try:
            seen = set()
            for h in search("CLINICAL_TRIALS_RESEARCH_DATABASE.CT.CLINICAL_TRIALS_SEARCH_SERVICE", topic,
                            ["NCT_ID", "BRIEF_TITLE", "OVERALL_STATUS", "STUDY_URL"], 10):
                if h.get("NCT_ID") in seen or len(seen) == 4:
                    continue
                seen.add(h.get("NCT_ID"))
                st.markdown(f'<div class="paper"><a href="{h.get("STUDY_URL", "")}" target="_blank">{h.get("BRIEF_TITLE")}</a>'
                            f'<div class="muted">{h.get("NCT_ID")} · {h.get("OVERALL_STATUS", "")}</div></div>',
                            unsafe_allow_html=True)
        except Exception as e:
            st.caption(f"Trials search unavailable: {str(e).splitlines()[0][:140]}")
    st.markdown('<div class="muted">Research summaries are for trainer education, not medical advice.</div>',
                unsafe_allow_html=True)

# ---------------------------------------------------------------- impact
with tab_impact:
    st.markdown("### Why it matters in South Australia")
    c = st.columns(3)
    card(c[0], "Serious claims from body stressing", "47.6%", "nursing, care and support workforce · Safe Work Australia",
         AMBER)
    ctx = q_or_none("""select
      (select coalesce(sum(total), 0) from H4H.HEALTH.A2_GEN_DATA_PEOPLE_USING_AGED_CARE_BY_REGION_30_JUNE_2025_4_RESIDENTIAL_CARE_SERVICE_LOCATION_TABLE_4_4_PHN
       where phn_code in ('PHN401','PHN402')) residential,
      (select coalesce(sum(total), 0) from H4H.HEALTH.A2_GEN_DATA_PEOPLE_USING_AGED_CARE_BY_REGION_30_JUNE_2025_2_HOME_CARE_RECIPIENT_LOCATION_TABLE_2_4_PHN
       where phn_2017_code in ('PHN401','PHN402')) home_care""")  # PHN401 Adelaide + PHN402 Country SA
    if ctx is not None:
        card(c[1], "Living in residential aged care, SA", f"{int(ctx['RESIDENTIAL'][0]):,}",
             "residents who depend on safe transfers every day · " + CONTEXT, GREEN)
        card(c[2], "Receiving home care packages, SA", f"{int(ctx['HOME_CARE'][0]):,}", CONTEXT, "#38bdf8")
    st.markdown('<div class="muted" style="margin-top:14px">Australian Institute of Health and Welfare, <i>GEN data: People '
                'using aged care by region data tables</i> (released 12 Feb 2026), 30 June 2025, residential care by '
                'service location, Table 4.4 (PHN); home care by recipient location, Table 2.4 (PHN). Via H4H Snowflake '
                '(H4H.HEALTH). Context only, not Safe Lift data; the two counts are not added together. '
                'Body-stressing share: Safe Work Australia WHS profile, nursing, care and support workforce.</div>',
                unsafe_allow_html=True)
    st.markdown("#### Recent sessions")
    st.dataframe(latest, use_container_width=True, hide_index=True)

st.markdown('<div class="muted" style="margin-top:28px;text-align:center">Safe Lift is a training aid, not a safety device '
            'or medical advice. Always follow the resident\'s manual handling plan. Built with Gemma 4, MediaPipe and '
            'Snowflake (Cortex Search, Snowflake ML, Marketplace) at Hack for Humanity Adelaide 2026.</div>',
            unsafe_allow_html=True)

if live:
    import time
    time.sleep(5)
    st.rerun()
