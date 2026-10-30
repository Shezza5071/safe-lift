# Safe Lift test set (SYNTHETIC)

Every record here is invented for testing. There are no real residents, workers or recordings. Do not present any figure from this set as evidence about real care work.

## How to use it

1. Copy this folder into the root of the `safe-lift` repo and name it `testdata/`.
2. Run the evaluation from the repo root:

   ```bash
   .venv/bin/python testdata/eval.py
   ```

   This runs the repo's own `reba.Scorer` over every staged session and checks it raises the alarm when it should and stays quiet when it shouldn't. It also reports how well the two human raters agree on each DINO item.
3. To test Gemma, fill `gemma_predictions_TEMPLATE.csv` with Gemma's DINO suggestions (save it as `gemma_predictions.csv`), and optionally write a `gate_predictions.csv` with columns `session_id,gate` (allow or block). Then run:

   ```bash
   .venv/bin/python testdata/eval.py --gemma testdata/gemma_predictions.csv --gate testdata/gate_predictions.csv
   ```

## What's in it

| File | Contents | Use it to test |
|---|---|---|
| `resident_plans.json` | 12 synthetic manual handling plans: mobility category, staff required, required aids, method per task | Plan-to-rules logic |
| `plans_text/R01.txt` … `R12.txt` | The same plans as plain text, as a carer would read them | Gemma reading a plan and producing the rules JSON |
| `sessions.csv` | 40 staged transfer sessions: who, which resident and task, staff and aids present, aid used, **expected gate result and expected alarm** | Setup gate and alarm accuracy |
| `frames_10hz.csv` | Trunk, twist and knee angles plus landmark visibility, 10 frames a second for 20 s per session (gate-blocked sessions have none) | `reba.Scorer`: thresholds, 2 s hold, median filter, visibility filter |
| `events_2s.csv` | One reading every 2 s in the repo's `EVENTS` table format | Loading the Snowflake table and dashboard tiles |
| `dino_ratings.csv` | DINO scores for each session from two independent raters (A and B), 16 items | Inter-rater agreement; the reference for Gemma's suggestions |
| `dino_items.json` | The 16 DINO items, phase, scale and description | Gemma prompt and function-calling schema |
| `skeletons/Sxxx_worst.png` | Skeleton-only side view of each session's worst moment | Gemma's post-alarm question and debrief |
| `units_mapo_inputs.csv` | Three synthetic care units: resident mobility mix, staffing by shift, hoist numbers, environment, training | A MAPO-style unit risk tile |
| `gemma_predictions_TEMPLATE.csv` | Blank sheet for Gemma's DINO suggestions | Scoring Gemma against the human raters |
| `eval.py` | The evaluation script | Everything above |

## The 11 scenarios

| Scenario | Sessions | What happens | Right answer |
|---|---|---|---|
| A good hoist | 6 | Hoist transfer per plan, upright | No alarm |
| B good slide sheet | 5 | Brief forward lean under 60° | No alarm |
| C good standing aid | 4 | Knees bent, trunk mostly upright | No alarm |
| D stoop lift | 5 | Plan breach: manual lift, trunk over 60° for about 3.5 s | Alarm |
| E twist pivot | 5 | Reaching across the bed, trunk about 35° plus twist about 35° | Alarm |
| F brief red | 3 | Red for about 1.2 s only (bending to lock brakes) | No alarm (tests the 2 s hold) |
| G spike artefact | 3 | Single-frame tracking glitches to 120° | No alarm (tests the median filter) |
| H occlusion | 2 | Real stoop, but a second worker blocks the camera | Missed: a known camera limitation |
| I gate: staff | 3 | Plan says 2 staff, 1 present | Gate blocks |
| J gate: aid | 2 | Plan needs a hoist, none in the room | Gate blocks |
| K borderline | 2 | Trunk oscillates 56–64° | Either outcome acceptable |

## How the data was built

- Angles follow the repo's thresholds: amber over 20° trunk flexion; red over 60°, or over 20° with twist over 20°, held 2 s. Noise of about 2° is added to every frame.
- DINO items follow Johnsson et al. (2004), *Applied Ergonomics* 35(6):591–601, as itemised in the Persian validation study (Jundishapur J Health Sci). Preparation and result items score 0 or 1; performance items score 0 to 1 in quarter steps; total 0–16.
- Rater B disagrees with rater A on about 8% of items at random, so the agreement figures resemble a real two-rater check.
- Unit inputs list the raw counts the MAPO method uses (Menoni et al. 1999, *Med Lav* 90:152–172). The MAPO factor values themselves are not included; take them from the published method tables before computing an index.
- Generated with a fixed random seed, so it is reproducible.

## Limits

- Synthetic angles are smoother and cleaner than real 2D pose data, which carries about 5–10° error. Expect lower accuracy on real staged lifts. Record 10–20 real staged transfers with consenting adults and two human raters before claiming any accuracy figure.
- The skeleton images are simple side views drawn from the angles, not MediaPipe output.
