# Safe Lift

A Gemma-coached manual handling trainer for care workers (Hack for Humanity Adelaide 2026).
MediaPipe is the eyes, Gemma is the coach, Snowflake is the memory. The build plan and roles are in `PLAN.md` (section v3).

> Training aid only, not a safety device or medical advice. The camera analyses movement live and saves no video. Use only with the consent of everyone in view.

## Run it

```bash
uv venv --python 3.13 .venv && uv pip install --python .venv/bin/python -r requirements.txt
mkdir -p models && curl -sSL -o models/pose_landmarker_lite.task \
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task
.venv/bin/python -m pytest -q
.venv/bin/python safelift.py --task bed_to_chair --staff S01   # q quits, d shows degrees
```

- **Gemma:** set `GEMINI_API_KEY` (your own key from Google AI Studio). Model `gemma-4-26b-a4b-it`.
- **Snowflake (optional):** a connection named `main` in `~/.snowflake/connections.toml`. Without it, readings go to `data/events.csv`.

## Files

| File | What it does |
|---|---|
| `reba.py` | REBA trunk bands from pose landmarks (amber > 20°, red > 60° or > 20° with twist, held 2 s) |
| `safelift.py` | Live camera window, alarm and beep, background writer to Snowflake |
| `gemma.py` | Gemma calls with retry, 20 s timeout and a labelled cache |
| `gate.py` | Setup gate: `read_plan` turns a SYNTHETIC plan photo into plan rules JSON; `check_room` has Gemma check a room photo against them by function calling (`set_checklist`, `block_task`, `allow_task`) and `draw_gate_panel` shows BLOCKED / READY. Try `python gate.py room demo/plan_demo_two_staff.png demo/room_1.jpg demo/room_2.jpg` |
| `demo/make_plans.py` | Renders the SYNTHETIC plan images in `demo/` (macOS font path) |
| `dashboard/streamlit_app.py` | Trainer dashboard (Streamlit in Snowflake) |
| `load_guidance.py` | Loads official guidance into Cortex Search |
| `ml.py` | Live ML risk flag: scores the latest reading with the Snowflake model (badge in the camera window) |
| `teach.py` | Gemma as a second rater: rates every reading's skeleton good/bad into `GEMMA_LABELS` |
| `sql/features.sql`, `sql/train.sql`, `sql/teach.sql` | Feature view, Snowflake ML classifier, and the Gemma-teaches-Snowflake comparison (run with `sql/run.py`) |

## How Gemma and Snowflake work together

1. **The camera measures.** MediaPipe pose landmarks become trunk, twist and knee angles every frame; the REBA rule drives the instant alarm.
2. **Gemma reasons.** It reads the handling plan, checks the room (setup gate), asks a specific question after a red alarm, and writes the debrief in the trainee's language, grounded in official guidance retrieved by **Cortex Search**.
3. **Snowflake learns.** Readings stream into `H4H.APP.EVENTS`. Trainers label lifts good or bad; a **Snowflake ML classifier** learns what *these trainers* call unsafe and flags each reading live.
4. **Gemma teaches Snowflake.** Gemma rates every reading's skeleton as a second rater. Readings where Gemma and the human disagree are dropped before training, and four raters (REBA rule, Gemma alone, ML on human labels, ML on Gemma-cleaned labels) are compared on the same held-out lifts (`MODEL_COMPARE`).

## Limits

Staged lifts by a few people in one room; small labelled sets; 2D pose from one camera (about 5 to 10 degrees of error). Numbers are evidence that the pipeline works, not proof of injury prevention.

## Next steps

- **Gemma inside Snowflake:** serve Gemma from the Snowflake Model Registry (Hugging Face integration) on a GPU compute pool, so care plans and posture data never leave the provider's own Snowflake account. Not possible on tonight's trial account (no external access, gated weights).
- More labelled lifts from real trainers across many workers, then retrain.

## Credits and licences

MIT licence. Gemma 4 ([terms](https://ai.google.dev/gemma/terms)), MediaPipe (Apache 2.0).
Guidance: Safe Work Australia, SafeWork NSW, WorkSafe Victoria. REBA: Hignett and McAtamney (2000), Applied Ergonomics 31(2):201-205.
