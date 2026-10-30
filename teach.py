"""Gemma as a second rater: rate every saved reading skeleton safe/unsafe and store it in Snowflake.

Run: .venv/bin/python teach.py <session_id> [<session_id> ...]
Reads snapshots/readings/<session>_<ts>.png (saved by safelift.py), writes H4H.APP.GEMMA_LABELS.
Gemma sees only the skeleton and the task, never the human label or the REBA band.
"""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import snowflake.connector

import gemma

READINGS = Path(__file__).parent / "snapshots" / "readings"
PROMPT = """You are an experienced manual handling trainer for aged care workers.
The image is a side-view stick figure (skeleton only) of a trainee during a practice task: {task}.
Judge ONLY the posture shown: is this a safe or unsafe way to be positioned for this task?
Unsafe signs: stooping with straight legs, trunk bent far forward, twisting, reaching away from the body.
Safe signs: upright trunk, or squatting with bent knees and a straight back, load close to the body.
JSON: {{"label": "good" or "bad", "confidence": number 0 to 1, "reason": "max 12 words"}}"""


def rate(path, task):
    try:
        out, src = gemma.gemma_json(PROMPT.format(task=task.replace("_", " ")), path)
        label = out.get("label")
        if label not in ("good", "bad"):
            return None
        return label, float(out.get("confidence", 0)), str(out.get("reason", ""))[:200], src
    except Exception as e:
        print("  skip", path.name, e.__class__.__name__)
        return None


def main(sessions):
    conn = snowflake.connector.connect(connection_name="main")
    c = conn.cursor()
    c.execute("""create table if not exists H4H.APP.GEMMA_LABELS (session_id string, ts timestamp_ntz,
                 gemma_label string, confidence float, reason string, source string)""")
    for s in sessions:
        task = c.execute("select any_value(task) from H4H.APP.EVENTS where session_id=%s", (s,)).fetchone()[0]
        done = {r[0].strftime("%Y-%m-%dT%H%M%S") for r in c.execute(
            "select ts from H4H.APP.GEMMA_LABELS where session_id=%s", (s,)).fetchall()}
        files = [p for p in sorted(READINGS.glob(f"{s}_*.png")) if p.stem.split("_", 1)[1] not in done]
        print(f"{s}: {len(files)} skeletons to rate (task {task})")
        with ThreadPoolExecutor(max_workers=6) as pool:  # ponytail: fixed concurrency; lower it if Gemma rate-limits
            results = list(pool.map(lambda p: (p, rate(p, task)), files))
        rows = []
        for p, r in results:
            if r:
                stamp = p.stem.split("_", 1)[1]  # 2026-10-30T180102
                ts = f"{stamp[:10]} {stamp[11:13]}:{stamp[13:15]}:{stamp[15:17]}"
                rows.append((s, ts, *r))
        if rows:
            c.executemany("insert into H4H.APP.GEMMA_LABELS values (%s, %s, %s, %s, %s, %s)", rows)
        print(f"  rated {len(rows)}/{len(files)}")
    conn.close()


if __name__ == "__main__":
    main(sys.argv[1:])
