"""Safe Lift analytics (Streamlit in Snowflake).

Analyses every reading streamed into H4H.APP from training sessions, plus H4H.HEALTH open data and two
Snowflake Marketplace Cortex Search services (PubMed Biomedical Research Corpus, Clinical Trials Research Database).
No outside calls. No per-worker breakdowns: patterns are by task and plan, never by person.
"""
import json

import altair as alt
import pandas as pd
import streamlit as st
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Safe Lift · manual handling analytics", page_icon="🦺", layout="wide")
s = get_active_session()

GREEN, AMBER, RED, INDIGO, SKY, INK, MUTED = "#16a34a", "#d97706", "#dc2626", "#4f46e5", "#0284c7", "#0f172a", "#64748b"
CONTEXT = "Context (AIHW GEN, 30 June 2025)"

st.markdown(f"""<style>
.stApp {{ background: #ffffff; color: {INK}; }}
.block-container {{ padding-top: 1.4rem; max-width: 1400px; }}
.head {{ display:flex; justify-content:space-between; align-items:flex-end; padding-bottom: 14px;
  border-bottom: 1px solid #e2e8f0; margin-bottom: 18px; }}
.head h1 {{ margin:0; font-size: 1.9rem; letter-spacing:-0.02em; color:{INK}; }}
.head .sub {{ color:{MUTED}; font-size: .95rem; margin-top: 2px; }}
.card {{ padding: 16px 18px; border-radius: 14px; background: #ffffff; border: 1px solid #e2e8f0;
  box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 4px 14px rgba(15,23,42,.04); height: 100%; }}
.card .k {{ color:{MUTED}; font-size:.78rem; text-transform: uppercase; letter-spacing:.07em; font-weight:600; }}
.card .v {{ font-size: 2rem; font-weight: 750; margin-top: 4px; }}
.card .s {{ color:{MUTED}; font-size:.82rem; margin-top: 2px; }}
.note {{ padding: 16px 18px; border-radius: 14px; background: #f8fafc; border: 1px solid #e2e8f0; line-height:1.6; }}
.paper {{ padding: 12px 14px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 10px; background:#fff; }}
.paper a {{ color:{INDIGO}; text-decoration:none; font-weight:600; }}
.muted {{ color:{MUTED}; font-size:.84rem; }}
.stTabs [data-baseweb="tab"] {{ font-size: 1rem; font-weight: 600; }}
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


def chart(c, height=280):
    return (c.properties(height=height).configure_view(strokeWidth=0)
            .configure_axis(labelColor=MUTED, titleColor=MUTED, gridColor="#f1f5f9", domainColor="#e2e8f0")
            .configure_legend(labelColor=INK, titleColor=MUTED))


BANDS = alt.Scale(domain=["green", "amber", "red"], range=[GREEN, AMBER, RED])

tot = q("""select count(distinct session_id) sessions, count(*) readings, count(distinct task) tasks,
  round(100*avg(iff(reba_band='green',1,0))) pct_safe, round(100*avg(iff(reba_band='red',1,0)),1) pct_red,
  sum(iff(alarm,1,0)) alarm_readings, count(label) labelled, min(ts) first_ts, max(ts) last_ts
  from H4H.APP.EVENTS""").iloc[0]
updated = q("select convert_timezone('Australia/Adelaide', current_timestamp())::timestamp_ntz as n")["N"][0]

st.markdown(f"""<div class="head"><div><h1>🦺 Safe Lift · manual handling analytics</h1>
<div class="sub">Posture readings streamed from training sessions, analysed in Snowflake. Patterns by task and plan, never by person.</div></div>
<div class="muted">Data {pd.to_datetime(tot['FIRST_TS']):%d %b %H:%M} to {pd.to_datetime(tot['LAST_TS']):%d %b %H:%M} · refreshed {updated:%H:%M} Adelaide</div></div>""",
            unsafe_allow_html=True)

if not tot["READINGS"]:
    st.info("No readings yet.")
    st.stop()

tab_over, tab_risk, tab_model, tab_ev, tab_ctx = st.tabs(
    ["Overview", "Risk patterns", "Risk model", "Research evidence", "South Australia context"])

# ---------------------------------------------------------------- overview
with tab_over:
    c = st.columns(5)
    card(c[0], "Training sessions", f"{int(tot['SESSIONS'])}", f"{int(tot['TASKS'])} task types")
    card(c[1], "Posture readings", f"{int(tot['READINGS']):,}", "one every 2 s, skeleton only")
    card(c[2], "Time in safe band", f"{tot['PCT_SAFE']:.0f}%", "trunk bend ≤ 20°", GREEN)
    card(c[3], "Time in high-risk band", f"{tot['PCT_RED']:.1f}%", "> 60°, or > 20° with twist, held 2 s", RED)
    card(c[4], "Labelled readings", f"{int(tot['LABELLED'])}", "trainer-labelled, for the risk model", INDIGO)

    st.markdown("#### Risk band mix by session")
    mix = q("""select e.session_id, s.started, s.task, e.reba_band, count(*) n
               from H4H.APP.EVENTS e
               join (select session_id, min(ts) started, any_value(task) task from H4H.APP.EVENTS group by 1) s
                 on s.session_id = e.session_id
               group by 1, 2, 3, 4""")
    mix["session"] = pd.to_datetime(mix["STARTED"]).dt.strftime("%d %b %H:%M") + " · " + mix["TASK"].str.replace("_", " ")
    st.altair_chart(chart(alt.Chart(mix).mark_bar().encode(
        x=alt.X("sum(N):Q", stack="normalize", title="share of readings", axis=alt.Axis(format="%")),
        y=alt.Y("session:N", sort=alt.SortField("STARTED"), title=None),
        color=alt.Color("REBA_BAND:N", scale=BANDS, title="band", sort=["green", "amber", "red"]),
        order=alt.Order("REBA_BAND:N", sort="descending"),
        tooltip=["session", "REBA_BAND", "N"]), 60 + 34 * mix["SESSION_ID"].nunique()), use_container_width=True)

    left, right = st.columns([3, 2])
    with left:
        deb = q("select language, debrief, citations, source, ts from H4H.APP.DEBRIEFS order by ts desc limit 1")
        if not deb.empty:
            d = deb.iloc[0]
            st.markdown(f"#### Latest coaching feedback · {d['LANGUAGE']}" + (" · cached" if d["SOURCE"] == "cache" else ""))
            st.markdown(f'<div class="note">{d["DEBRIEF"]}</div>', unsafe_allow_html=True)
            cites = "; ".join(f"[{i + 1}] {c}" for i, c in enumerate(json.loads(d["CITATIONS"])))
            st.markdown(f'<div class="muted" style="margin-top:6px">Written by Gemma, grounded in official guidance '
                        f'via Cortex Search: {cites}</div>', unsafe_allow_html=True)
    with right:
        st.markdown("#### Why high-risk moments happened")
        lab = q("select answer, count(*) n from H4H.APP.ALARM_LABELS group by 1 order by 2 desc")
        if lab.empty:
            st.markdown('<div class="muted">Trainee answers to Gemma\'s follow-up question will appear here.</div>',
                        unsafe_allow_html=True)
        else:
            st.altair_chart(chart(alt.Chart(lab).mark_bar(cornerRadiusEnd=4, color=INDIGO).encode(
                x=alt.X("N:Q", title="answers"), y=alt.Y("ANSWER:N", sort="-x", title=None)), 200),
                use_container_width=True)

# ---------------------------------------------------------------- risk patterns
with tab_risk:
    st.markdown("#### High-risk share by task")
    st.markdown('<div class="muted">Where tasks repeatedly go red, review the task, the equipment and the handling plan.</div>',
                unsafe_allow_html=True)
    bytask = q("""select task, count(*) readings, round(100*avg(iff(reba_band='red',1,0)),1) pct_red,
                  round(100*avg(iff(reba_band='amber',1,0)),1) pct_amber, round(avg(trunk_deg)) avg_trunk,
                  round(max(trunk_deg)) max_trunk from H4H.APP.EVENTS group by 1 order by pct_red desc""")
    long = bytask.melt(id_vars=["TASK"], value_vars=["PCT_AMBER", "PCT_RED"], var_name="band", value_name="pct")
    long["band"] = long["band"].map({"PCT_AMBER": "amber", "PCT_RED": "red"})
    st.altair_chart(chart(alt.Chart(long).mark_bar(cornerRadiusEnd=4).encode(
        x=alt.X("pct:Q", title="% of readings"), y=alt.Y("TASK:N", title=None, sort="-x"),
        color=alt.Color("band:N", scale=BANDS, title="band"), yOffset="band:N",
        tooltip=["TASK", "band", "pct"]), 70 + 60 * len(bytask)), use_container_width=True)

    a, b = st.columns(2)
    with a:
        st.markdown("#### Trunk bend distribution")
        hist = q("""select width_bucket(trunk_deg, 0, 120, 12) * 10 - 10 as bend, reba_band, count(*) n
                    from H4H.APP.EVENTS group by 1, 2""")
        st.altair_chart(chart(alt.Chart(hist).mark_bar().encode(
            x=alt.X("BEND:O", title="trunk bend (°, 10° bins)"), y=alt.Y("sum(N):Q", title="readings"),
            color=alt.Color("REBA_BAND:N", scale=BANDS, title="band"), tooltip=["BEND", "REBA_BAND", "N"])),
            use_container_width=True)
    with b:
        st.markdown("#### Bend and twist together")
        pts = q("select trunk_deg, twist_deg, reba_band from H4H.APP.EVENTS sample (600 rows)")
        st.altair_chart(chart(alt.Chart(pts).mark_circle(size=38, opacity=0.6).encode(
            x=alt.X("TRUNK_DEG:Q", title="trunk bend (°)"), y=alt.Y("TWIST_DEG:Q", title="twist (°)"),
            color=alt.Color("REBA_BAND:N", scale=BANDS, title="band"))), use_container_width=True)
    st.markdown('<div class="muted">Single-camera pose is about ±5 to 10°; read the bands, not exact degrees.</div>',
                unsafe_allow_html=True)
    st.dataframe(bytask.rename(columns={"TASK": "Task", "READINGS": "Readings", "PCT_RED": "% high risk",
                                        "PCT_AMBER": "% caution", "AVG_TRUNK": "Avg bend °", "MAX_TRUNK": "Max bend °"}),
                 use_container_width=True, hide_index=True)

# ---------------------------------------------------------------- risk model
with tab_model:
    st.markdown("#### Snowflake ML risk model, taught by Gemma")
    st.markdown('<div class="note">Trainers label lifts good or bad. <b>Gemma</b> rates every reading\'s skeleton as a '
                'second rater, and readings where the two disagree are removed. A <b>Snowflake ML classifier</b> learns '
                'from the cleaned labels and scores readings as they stream in. The audible alarm always follows the '
                'REBA angle rule; the model is an additional signal.</div>', unsafe_allow_html=True)
    compare = q_or_none("""select rater, ord, test_readings, accuracy_pct, bad_caught_pct, flags_correct_pct,
                           v1_train_rows, v2_train_rows from H4H.APP.MODEL_COMPARE order by ord""")
    if compare is not None and not compare.empty:
        best = compare.sort_values("ACCURACY_PCT", ascending=False).iloc[0]["RATER"]
        c = st.columns(4)
        for col, (_, r) in zip(c, compare.iterrows()):
            card(col, r["RATER"], f"{r['ACCURACY_PCT']:.0f}%",
                 f"accuracy · catches {r['BAD_CAUGHT_PCT']:.0f}% of risky readings" if pd.notna(r["BAD_CAUGHT_PCT"])
                 else "accuracy", INDIGO if r["RATER"] == best else INK)
        long = compare.melt(id_vars=["RATER", "ORD"], value_vars=["ACCURACY_PCT", "BAD_CAUGHT_PCT", "FLAGS_CORRECT_PCT"],
                            var_name="measure", value_name="pct")
        long["measure"] = long["measure"].map({"ACCURACY_PCT": "accuracy", "BAD_CAUGHT_PCT": "risky readings caught",
                                               "FLAGS_CORRECT_PCT": "flags that were right"})
        st.altair_chart(chart(alt.Chart(long).mark_bar(cornerRadiusEnd=4).encode(
            x=alt.X("pct:Q", title="%", scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("RATER:N", sort=alt.SortField("ORD"), title=None),
            color=alt.Color("measure:N", scale=alt.Scale(range=[INDIGO, GREEN, SKY]), title=None,
                            legend=alt.Legend(orient="top")),
            yOffset="measure:N", tooltip=["RATER", "measure", "pct"]), 340), use_container_width=True)
        st.markdown(f'<div class="muted">Held-out test of {int(compare["TEST_READINGS"].max())} trainer-labelled readings '
                    f'from staged lifts. Model trained on {int(compare["V1_TRAIN_ROWS"].max())} readings (human labels) vs '
                    f'{int(compare["V2_TRAIN_ROWS"].max())} (Gemma-cleaned). Early evidence, not a validated safety measure.</div>',
                    unsafe_allow_html=True)

    agree = q_or_none("""select session_id, count(*) n, round(100*avg(iff(rule_bad = ml_bad, 1, 0))) pct_agree,
      sum(iff(ml_bad, 1, 0)) ml_flags, sum(iff(rule_bad, 1, 0)) rule_flags
      from H4H.APP.MODEL_EVAL group by 1 order by max(ts) desc limit 1""")
    allr = q_or_none("select count(*) n, round(100*avg(iff(rule_bad = ml_bad, 1, 0))) pct_agree from H4H.APP.MODEL_EVAL")
    gem = q_or_none("select human, gemma, n from H4H.APP.GEMMA_AGREEMENT")
    a, b = st.columns([3, 2])
    with a:
        if allr is not None and allr["N"][0]:
            k = st.columns(2)
            if agree is not None and not agree.empty and pd.notna(agree["PCT_AGREE"][0]):
                card(k[0], f"Model vs REBA rule, latest scored session ({agree['SESSION_ID'][0]})",
                     f"{agree['PCT_AGREE'][0]:.0f}%",
                     f"model flags {int(agree['ML_FLAGS'][0])} · rule high-risk {int(agree['RULE_FLAGS'][0])}", SKY)
            card(k[1], "Model vs REBA rule, all readings",
                 f"{allr['PCT_AGREE'][0]:.0f}%" if pd.notna(allr["PCT_AGREE"][0]) else "n/a",
                 f"{int(allr['N'][0])} readings scored", SKY)
    with b:
        if gem is not None and not gem.empty:
            st.markdown("**Trainer vs Gemma labels**")
            st.altair_chart(alt.Chart(gem).mark_rect(cornerRadius=6).encode(
                x=alt.X("GEMMA:N", title="Gemma"), y=alt.Y("HUMAN:N", title="Trainer"),
                color=alt.Color("N:Q", scale=alt.Scale(scheme="blues"), legend=None)).properties(height=150)
                + alt.Chart(gem).mark_text(fontSize=16, fontWeight="bold").encode(x="GEMMA:N", y="HUMAN:N", text="N:Q"),
                use_container_width=True)

# ---------------------------------------------------------------- research evidence
with tab_ev:
    st.markdown("#### What the research says")
    st.markdown('<div class="muted">Cortex Search over Snowflake Marketplace datasets: PubMed Biomedical Research Corpus '
                'and the Clinical Trials Research Database. For trainer education, not medical advice.</div>',
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
        st.markdown("**PubMed studies**")
        try:
            seen = set()
            for h in search("PUBMED_BIOMEDICAL_RESEARCH_CORPUS.OA_COMM.PUBMED_CKE", topic,
                            ["TITLE", "CITATION", "ARTICLE_URL", "CHUNK"], 8):
                if h.get("TITLE") in seen or len(seen) == 4:
                    continue
                seen.add(h.get("TITLE"))
                st.markdown(f'<div class="paper"><a href="{h.get("ARTICLE_URL", "")}" target="_blank">{h.get("TITLE")}</a>'
                            f'<div class="muted">{(h.get("CITATION") or "")[:160]}</div>'
                            f'<div style="margin-top:6px;font-size:.88rem;color:{INK}">“{(h.get("CHUNK") or "")[:240].strip()}…”</div></div>',
                            unsafe_allow_html=True)
        except Exception as e:
            st.caption(f"PubMed search unavailable: {str(e).splitlines()[0][:140]}")
    with t_col:
        st.markdown("**Clinical trials**")
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

# ---------------------------------------------------------------- SA context
with tab_ctx:
    st.markdown("#### Why safe transfers matter in South Australia")
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
        card(c[2], "Receiving home care packages, SA", f"{int(ctx['HOME_CARE'][0]):,}", CONTEXT, SKY)
    st.markdown('<div class="muted" style="margin-top:14px">Australian Institute of Health and Welfare, <i>GEN data: People '
                'using aged care by region data tables</i> (released 12 Feb 2026), 30 June 2025, residential care by '
                'service location, Table 4.4 (PHN); home care by recipient location, Table 2.4 (PHN). Via H4H Snowflake '
                '(H4H.HEALTH). Context only, not Safe Lift data; the two counts are not added together. '
                'Body-stressing share: Safe Work Australia WHS profile, nursing, care and support workforce.</div>',
                unsafe_allow_html=True)

st.markdown(f'<div class="muted" style="margin-top:28px;text-align:center;border-top:1px solid #e2e8f0;padding-top:12px">'
            'Safe Lift is a training aid, not a safety device or medical advice. Always follow the resident\'s manual '
            'handling plan. Gemma 4 · MediaPipe · Snowflake (Cortex Search, Snowflake ML, Marketplace).</div>',
            unsafe_allow_html=True)
