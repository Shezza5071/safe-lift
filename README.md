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

## Credits and licences

MIT licence. Gemma 4 ([terms](https://ai.google.dev/gemma/terms)), MediaPipe (Apache 2.0).
Guidance: Safe Work Australia, SafeWork NSW, WorkSafe Victoria. REBA: Hignett and McAtamney (2000), Applied Ergonomics 31(2):201-205.
