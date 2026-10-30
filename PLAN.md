# Safe Lift: build memo (v3) for Hack for Humanity Adelaide

## DECISION (29 Oct): the user chose Safe Lift for Friday. Section "v3" below overrides everything after it.

## v3: final design, scope and run sheet (after 3 judging rounds, WHS and privacy red teams)
**Principle:** MediaPipe is the eyes, Gemma is the coach, Snowflake is the memory.
**Scores v3 (independent AI judges, /10):** Gemma 7, open-source 7, Snowflake 7, humanity 7 (v1 was 6/5/6/6). Back Door Navigator scored 9/8/9/9; the gap is structural (live alarm is not Gemma; training-room benefit). Realistic ceiling with the fixes below plus a real trainer quote: about 8. Build odds: T1 72%, T1+T2 35%.

### The hook
**The setup gate:** Gemma reads the resident's (synthetic) manual handling plan, then checks the room: "Plan says two staff, one seen." The lift is blocked until the plan is met. Posture scoring is the supporting act.

### Final scope
- **T1 (must):** live REBA alarm (amber over 20 deg, red over 60 deg or over 20 deg with twist for 2 s; visibility filter, clamp, 5-frame median); angle numbers stream to Snowflake; Streamlit-in-Snowflake trainer dashboard with LIVE badge and Adelaide time; after each red alarm Gemma looks at the skeleton-only snapshot and asks a **specific** question ("your trunk is bent and twisted left; were you reaching across the bed?"), answered by tapping an option; Gemma debrief citing Cortex Search guidance, with a language parameter (Vietnamese or Nepali); `gemma()` wrapper with retry, 20 s timeout and labelled cache.
- **T2 (visible extras):** plan-to-rules JSON (configures the checklist and alarm profile); setup gate via function calling (`set_checklist`, `block_task`) showing the call JSON in the Gemma panel; TOP_INSIGHTS and ANOMALY_DETECTION tiles (run on live rows, or on the history clearly labelled SYNTHETIC and showing the live session moving it); Marketplace estimate tile ("Employment - Statistics - Australia - Free", labelled estimate, join SQL visible); masking policy shown in two Snowsight worksheet tabs (trainer vs worker).
- **Only if green at 5:45:** pattern coach agent with 2 tools (`get_top_insights`, `search_guidance`).
- **Cut (README "next steps" only):** Model Registry classifier (10 staged lifts cannot train it honestly), secure data sharing, Snowflake Alert (the tested task covers it), FORECAST tile, AI_CLASSIFY, row access policy inside Streamlit (apps run with owner's rights, so the role does not switch per viewer), dictation polish, Ollama unless pulled before Friday.

### Demo (one story, under 2:50)
1. **0:00 to 0:20:** a real SA trainer quote (get one tonight) plus the 47.6% / 21% stats; "training alone doesn't work; following the plan does".
2. **0:20 to 0:50:** Gemma reads the plan, then the setup gate **blocks** the lift ("one staff seen"). The Gemma panel shows the function call.
3. **0:50 to 1:40:** the second trainee joins and the lift unlocks; a bad lift goes red and beeps; Gemma asks its specific question; tap the answer.
4. **1:40 to 2:15:** a debrief in Nepali or Vietnamese with a citation to the Model Code of Practice.
5. **2:15 to 2:35:** trainer dashboard: TOP_INSIGHTS pattern, anomaly flag, compliance rate; masking shot.
6. **2:35 to 2:50:** one closing beat: the CoCo clip (prompt, SQL, caught bug), the Marketplace estimate tile, a fresh clone running `make eval`, MIT plus Apache 2.0.

### First 30 minutes (3:45 to 4:15)
- **Builder:** tag the baseline camera, REBA and alarm build; `gemma()` wrapper; record a 60 s fallback video of the live alarm.
- **Data:** seed a labelled SYNTHETIC 4-week history; rerun TOP_INSIGHTS and ANOMALY; load the guidance PDFs (AI_PARSE_DOCUMENT) into Cortex Search once and save 3 known-good queries; mount the Marketplace listing and compute the estimate table; capture the CoCo clip.
- **Demo lead:** photograph the synthetic plan; stage the training-room photo with 1 and then 2 people; run both through Gemma once and cache; script with exact click path; consent and disclaimer slide; occlusion test position.

### Gates
- **5:00:** T1 runs end to end twice on the demo laptop. If not, everyone fixes T1, and the setup gate and coach are dropped.
- **5:45:** plan-to-rules and setup gate working (cached fallback labelled); dashboard tiles live; masking shot ready. Coach only if all green.
- **6:15:** feature freeze. Repo public (MIT), README complete, timed rehearsal under 3 min.

### Snowflake full-stack tests (29 Oct, trial account): all PASS
Masking policy (trainer role sees `***` for staff codes), row access policy (trainer sees only permitted rows), Snowflake Alert, Model Registry (log_model needs `options={'embed_local_ml_library': True}` because snowflake-ml-python >=2.7 is not in the account's package channel), secure share with a secure view. In the plan only the **masking shot** is used; the rest stay on the cut list. Test objects and their DROP order are in the session log; the masking policy is still applied to `H4H.APP.CAPTEST_EVENTS.session_id`.

### Open source extras the judges asked for
`reba.py` with pytest; the plan-to-rules JSON schema as an open spec with 3 synthetic sample plans; `make eval` (alarm precision and recall plus Gemma cause-label agreement on 10 staged lifts, limits stated); clean clone runs in local CSV mode with no Snowflake.

### Tonight (setup only)
- [ ] **Get a quote from a real SA Certificate III trainer or facility educator** (every judge asked for it).
- [ ] Get "Employment - Statistics - Australia - Free" in the Marketplace (and confirm it holds SA health-care headcount).
- [ ] Spare Gemini key; phone hotspot; tripod; HDMI adapter; plain backdrop; teammate in fitted clothing.
- [ ] Ask organisers on Discord: MediaPipe as a sensor, with Gemma doing the reasoning, OK?
- [ ] Optional: `ollama pull gemma4:e2b`.

---
# (v2 memo below, kept for reference)

> **Head-to-head verdict (29 Oct, four independent award judges):** Back Door Navigator won every award (Gemma 9 vs 6, open-source 8 vs 7, Snowflake 9 vs 6, humanity 9 vs 6). Safe Lift scored higher on creativity (8) and demo (8). Recommendation: build Back Door Navigator on Friday; keep this memo as the next project.
>
> **Ideas raised for a later version:** (a) after each alarm the worker labels the task (tap or type; voice needs a separate speech-to-text step because the Gemma API takes no audio); (b) repeating patterns per task from session history (Snowflake ML functions, see test results); (c) exercises or stretches: only as general, sourced wellbeing information with "see a physio", because personal exercise advice counts as medical advice (barred by the Gemini API terms), and the WHS review warns against shifting the fix onto the worker.

Friday 30 October 2026, 97 Pirie St. Build 3:45 to 6:50pm. Demos from 7:15pm.
Prepared 29 October 2026. Capability tests only were run before the event; **rebuild the app fresh on the day** (MLH rule: project work happens on the day). The throwaway test script is in the session scratchpad and is not project code.

## 1. Pitch (v2, after the WHS and privacy red teams)
"Body stressing is nearly half of all serious injury claims for Australia's care workforce. Training alone doesn't fix it; the evidence says equipment and following the resident's handling plan do. Safe Lift checks that the plan is followed before a transfer, watches the lift live with on-device pose tracking, and tells managers where equipment or plans are failing. Nothing is recorded."

- **Problem (sourced):** body stressing averaged **47.6%** of serious claims for the nursing, care and support workforce since 2012-13 ([Safe Work Australia profile](https://data.safeworkaustralia.gov.au/profile/whs-profile-nursing-care-support-workforce)); SA health care workers are **21%** of body-stressing claims ([SafeWork SA](https://www.safework.sa.gov.au/news-and-alerts/news/news/2024/campaign-to-combat-body-stressing-claims)); about half involve the resident as the cause.
- **Evidence that shapes the design:** a [Cochrane review](https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.CD005958.pub3/information) found manual handling advice and training alone does **not** prevent back pain. Training and prompts are the weakest tier of the WHS hierarchy of controls. So the headline is plan compliance and equipment, not "bend your knees".
- **Theme:** health. **Enter:** all three challenges plus the humanity mention.

## 2. What it does (user flow)
1. **Plan read (Gemma 4, vision):** photo of a synthetic manual handling plan, which Gemma turns into JSON rules: required equipment (hoist, slide sheet, standing aid), staff count, task type. These rules **set the checklist and the alarm profile** (Gemma decides; MediaPipe only measures).
2. **Setup check (Gemma 4, function calling: `set_checklist`, `block_task`):** a training-room photo. The lift is **blocked** until the plan's requirements are seen ("plan says two staff, one seen").
3. **Live lift (MediaPipe, on device, nothing saved):** REBA bands. **Amber:** trunk flexion over 20 deg. **Red:** over 60 deg, or over 20 deg with twist, sustained 2 s. Advice on screen: "Stop and use the equipment in the plan." Show bands, not exact degrees (2D pose error is about 5 to 10 deg).
4. **Debrief (Gemma 4):** a skeleton-only snapshot of the worst moment (pose drawn on a blank canvas, so no photo of a person goes to the API) plus the angle log. One concrete fix, citing official guidance retrieved by Cortex Search.
5. **Manager view (Streamlit in Snowflake):** readings, alarms, % time in each REBA band, plan-compliance rate, alarms by task; Gemma-written improvement suggestions that point to **task or plan review**, never worker blame.

## 3. Architecture (verified 29 Oct)
- **Live app:** ONE Python script with the proven **OpenCV window** (do not rebuild the live view in Streamlit). MediaPipe Pose Landmarker (lite model). All network calls (Snowflake inserts, Gemma) run in a **background thread and queue**, never in the camera loop.
- **Gemma 4:** `gemma-4-26b-a4b-it` via the Gemini API, `thinking_level="minimal"`. **Retry with backoff** (two transient 500 errors seen in testing). Strip code fences before parsing JSON. Cache responses as an emergency fallback, labelled.
- **Snowflake:** the laptop writes angle numbers every 2 s with `snowflake.connector.connect(connection_name="main")`. Dynamic table for session summaries. Task flags repeated alarms per task or plan. Streamlit in Snowflake reads tables; it **cannot call Gemma** (trial accounts block external access), so the laptop writes Gemma's text into a table and the dashboard displays it.

| Component | Test result (29 Oct) |
|---|---|
| MediaPipe 1.2.0 + OpenCV 5.0 in Python 3.13 venv | Installed; skeleton placed correctly on a test photo |
| Live camera window with alarm and beep | Works on the laptop (user confirmed) |
| Laptop to Snowflake inserts | 20 rows in ~0.65 s; 145 live readings captured |
| Dynamic table, task, Streamlit in Snowflake | All PASS on trial |
| Snowflake patterns, then Gemma suggestions, saved to Snowflake | PASS (3.8 s), after one retry |
| Gemma vision / function calling | PASS (7.6 s / 2.0 s) |
| Cortex Search, AI_PARSE_DOCUMENT | PASS |
| Two people plus bed (occlusion) | **NOT TESTED** |
| Gemma setup check on a realistic training-room photo | **NOT TESTED** |

**Known fixes to build in:** landmark visibility filter (skip landmarks below 0.6), clamp angles 0 to 120 deg, 5-frame median (the test produced impossible 166 deg readings); set timestamps to Australia/Adelaide (Snowflake stored US Pacific).

## 4. Snowflake objects to build on the day (schema `H4H.APP`)
- `EVENTS` (session_id, ts, task, trunk_deg, twist_deg, knee_deg, reba_band, alarm, staff_code). Anonymous staff code only; no images, no names.
- `SESSIONS` (plan rules JSON, setup check result, compliance flag).
- `INSIGHTS` (created_at, model, stats VARIANT, suggestions VARIANT): Gemma's text.
- Dynamic table `SESSION_SUMMARY`; task `FLAG_REPEATED_ALARMS` (per task or plan, not per worker).
- Cortex Search service over `GUIDANCE_CHUNKS` loaded from the official pages in section 8.
- **Marketplace:** "Employment - Statistics - Australia - Free", joined in a dynamic table to scale the live unsafe-lift rate into an **estimated** SA exposure figure that Gemma cites (label as estimate; check the listing actually holds SA health-care headcount after Get).
- Save every CoCo prompt and the SQL it wrote, plus one bug it caught, in `coco/`.

## 5. Roles
- **Builder:** the live script, Gemma calls, background thread.
- **Data (CoCo):** tables, dynamic table, task, dashboard, Marketplace join, Cortex Search, `coco/` evidence.
- **Demo lead:** synthetic plan photo, training-room setup photo, guidance chunks, README, slides, test subject, rehearsals, backup recording, submission.

## 6. Timeline and gates
| Time | Builder | Data | Demo lead |
|---|---|---|---|
| 3:45 | Repo (public, MIT), venv, run the camera loop, keys | Log in, create `EVENTS`, open dashboard | Pick demo spot and lighting; script outline |
| 4:00 | Visibility filter, clamp, median, REBA bands, 2 s hold | Dashboard: readings, alarms, bands, Adelaide time | Synthetic plan photo; draft Gemma prompts |
| 4:30 | Background queue: batched inserts | Dynamic table, verify live rows | README skeleton (Gemma 4, MediaPipe, licences) |
| **5:00 gate** | A full session end to end: skeleton, alarm on a bad lift and not a good one, rows in Snowflake, dashboard shows them. **If not: fix the core only.** | | |
| 5:00 | Gemma debrief at session end (skeleton snapshot + angle log, retry) | Cortex Search over guidance; Gemma insights table | Act test lifts; log false alarms |
| **5:45 gate** | Debrief appears in under 15 s every session. **If passed:** add plan read and setup check. **If not:** polish the debrief only | Task, Marketplace join, CoCo screenshots | Slides; cache Gemma outputs |
| **6:15 gate** | Feature freeze; tag a demo-safe commit | Freeze dashboard | Rehearsal 1, record backup run |
| 6:30 | Bug fixes only | Check refresh and time zone | Rehearsal 2 (under 3 min) |
| 6:50 | Submit on MLH | | |

**Feasibility (build-risk reviewer):** core 80%; core plus plan read and setup check 50%; everything 10%.

## 7. Demo (3 minutes)
1. **0:00 to 0:20:** one SA carer persona; the 47.6% and 21% figures on one slide; "training alone doesn't work, the evidence says equipment and plans do".
2. **0:20 to 0:50:** Gemma reads the synthetic plan ("hoist + 2 staff"); setup check blocks the lift ("one staff seen").
3. **0:50 to 1:50:** second teammate joins; the lift unlocks. A bad lift goes red and beeps; a good one stays green. Bands are readable from the back of the room.
4. **1:50 to 2:30:** Gemma's debrief citing the Model Code of Practice; the row appears in the Snowflake dashboard with the plan-compliance rate and the Marketplace estimate.
5. **2:30 to 3:00:** how it works (Gemma decides, MediaPipe measures, Snowflake analyses), privacy line ("nothing recorded, skeleton only, training-room mode"), what was new to the team.

## 8. Guidance to load into Cortex Search (verify current editions on the day)
- Model Code of Practice: Hazardous manual tasks: https://www.safeworkaustralia.gov.au/doc/model-code-practice-hazardous-manual-tasks
- Safe Work Australia, Lifting, pushing and pulling: https://www.safeworkaustralia.gov.au/safety-topic/hazards/lifting-pushing-and-pulling-manual-tasks
- WorkSafe Victoria, Transferring people safely: https://www.worksafe.vic.gov.au/resources/transferring-people-safely-handbook-workplaces
- WorkSafe Victoria, Transferring people from beds and chairs: https://www.worksafe.vic.gov.au/resources/transferring-people-beds-and-chairs-health-and-safety-solution
- SafeWork NSW, Aged care: https://www.safework.nsw.gov.au/your-industry/health-care-and-social-assistance/aged-care
- SafeWork SA aged care safety blitz (2024): https://safework.sa.gov.au/news-and-alerts/news/news/2024/safety-blitz-at-aged-care-homes
- REBA: Hignett and McAtamney (2000), Applied Ergonomics 31(2):201-205.

## 9. Privacy, law and claims (red team)
- **Demo:** consenting adult teammates and synthetic plans only; no residents, no bystanders in frame (Gemini free-tier terms forbid personal or sensitive data).
- **Real deployment:** the SA Surveillance Devices Act 2016 makes it an offence to *observe* a private activity without consent, even without recording. So **training-room mode is the default**; a care-setting mode needs consent recorded from the resident or their decision-maker.
- **Never:** real resident images or plans to the free API; saving raw frames; bathrooms or intimate care; discipline, rankings or rosters from alarm data; claims of injury prevention or certification.
- **Disclaimer:** "Safe Lift is a training aid, not a safety device or medical advice. Posture limits are indicative. Always follow the resident's manual handling plan and your employer's procedures. The camera analyses movement live and saves no video. Use only with consent of everyone in view."
- **Worker consent wording, room notice, and data retention (for example 90 days)** go in the README.

## 10. README must contain
What it does; Gemma 4 (`gemma-4-26b-a4b-it`, Gemini API, Apache 2.0 link) with each of its jobs; MediaPipe (Apache 2.0); data and credit lines; the Marketplace listing named; how CoCo helped (`coco/`); a small labelled angle CSV and alarm-precision eval on 10 staged lifts; limits, privacy and the disclaimer; one-command run; AI tools used. Repo licence: **MIT** (event rule).

## 11. Before Friday (setup only)
- [ ] Get "Employment - Statistics - Australia - Free" (and the Healthcare listing) in the Marketplace; check they say Free.
- [ ] Spare Gemini API key from a teammate.
- [ ] Phone hotspot, tripod or stand, charger, HDMI adapter, plain backdrop.
- [ ] Ask organisers on Discord: MediaPipe as a sensor with Gemma doing the reasoning, OK?
- [ ] A teammate with fitted clothing as the test subject; a training mannequin if available.
- [ ] Optional: `ollama pull gemma4:e2b` for the local open-weights flag.
- [ ] Register on MLH, RSVP on Luma.

## 12. Leftover test objects (drop when done)
`H4H.APP`: CAPTEST_EVENTS, CAPTEST_INSIGHTS, CAPTEST_EVENTS_SUMMARY (suspended), CAPTEST_TASK (suspended), CAPTEST_SIS + CAPTEST_SIS_STAGE, CAPTEST_GUIDE, CAPTEST_SEARCH, CAPTEST_STAGE, GEMINI_API_RULE.
