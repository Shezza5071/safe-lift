"""Safe Lift live coach: MediaPipe watches, REBA bands alarm, readings stream to Snowflake.

Run: .venv/bin/python safelift.py --task bed_to_chair --staff S01 --lang Nepali
Keys: q quits (then the Gemma debrief runs), d toggles degrees, 1-4 answers Gemma's alarm question,
g / b / n label the lift being performed now as good / bad / unlabelled (training data for the ML model).
No Snowflake connection -> rows go to data/<table>.csv instead.
"""
import argparse
import csv
import json
import queue
import subprocess
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

import gemma
import ml
import reba

ROOT = Path(__file__).parent
MODEL = ROOT / "models" / "pose_landmarker_lite.task"
ADL = ZoneInfo("Australia/Adelaide")
SAMPLE_S = 2.0
TABLES = {
    "EVENTS": ["session_id", "ts", "task", "trunk_deg", "twist_deg", "knee_deg", "reba_band", "alarm", "staff_code",
               "label"],
    "ALARM_LABELS": ["session_id", "ts", "task", "trunk_deg", "twist_deg", "question", "answer", "source"],
    "DEBRIEFS": ["session_id", "ts", "task", "language", "summary", "debrief", "citations", "source"],
}
DDL = {
    "EVENTS": "session_id string, ts timestamp_ntz, task string, trunk_deg float, twist_deg float, "
              "knee_deg float, reba_band string, alarm boolean, staff_code string, label string",
    "ALARM_LABELS": "session_id string, ts timestamp_ntz, task string, trunk_deg float, twist_deg float, "
                    "question string, answer string, source string",
    "DEBRIEFS": "session_id string, ts timestamp_ntz, task string, language string, summary variant, "
                "debrief string, citations variant, source string",
}
COLOURS = {"green": (60, 180, 75), "amber": (0, 165, 255), "red": (40, 40, 220)}
BONES = [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24), (23, 24),
         (23, 25), (25, 27), (24, 26), (26, 28)]


def now_adl():
    return datetime.now(ADL).strftime("%Y-%m-%d %H:%M:%S")


def connect():
    try:
        import snowflake.connector
        conn = snowflake.connector.connect(connection_name="main")
        for t, cols in DDL.items():
            conn.cursor().execute(f"create table if not exists H4H.APP.{t} ({cols})")
        conn.cursor().execute("alter table H4H.APP.EVENTS add column if not exists label string")  # pre-label tables
        return conn
    except Exception as e:
        print(f"[snowflake] unavailable ({e.__class__.__name__}), using data/*.csv")
        return None


def write(conn, table, rows):
    cols = TABLES[table]
    if conn:
        try:
            # variant columns need parse_json, so insert via select
            sel = ",".join(f"parse_json(column{i + 1})" if c in ("summary", "citations") else f"column{i + 1}"
                           for i, c in enumerate(cols))
            vals = ",".join(["(" + ",".join(["%s"] * len(cols)) + ")"] * len(rows))
            conn.cursor().execute(f"insert into H4H.APP.{table} ({','.join(cols)}) select {sel} from values {vals}",
                                  [v for r in rows for v in r])
            return
        except Exception as e:
            print(f"[snowflake] insert into {table} failed ({e}), CSV for this batch")
    out = ROOT / "data" / f"{table.lower()}.csv"
    out.parent.mkdir(exist_ok=True)
    new = not out.exists()
    with out.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(cols)
        w.writerows(rows)


def sink(q):
    """Background writer: batch (table, row) items every SAMPLE_S. None stops it."""
    conn = connect()
    stop = False
    while not stop:
        items = []
        try:
            items.append(q.get(timeout=SAMPLE_S))
            while True:
                items.append(q.get_nowait())
        except queue.Empty:
            pass
        stop = None in items
        by_table = {}
        for it in filter(None, items):
            by_table.setdefault(it[0], []).append(it[1])
        for table, rows in by_table.items():
            write(conn, table, rows)
    if conn:
        conn.close()


def guidance(query, k=3):
    """Top official-guidance chunks from Cortex Search; [] if Snowflake is unavailable."""
    try:
        import snowflake.connector
        with snowflake.connector.connect(connection_name="main") as conn:
            raw = conn.cursor().execute(
                "select snowflake.cortex.search_preview('H4H.APP.GUIDANCE_SEARCH', %s)",
                (json.dumps({"query": query, "columns": ["source", "chunk"], "limit": k}),)).fetchone()[0]
        return [{"source": r["source"], "text": r["chunk"]} for r in json.loads(raw)["results"]]
    except Exception as e:
        print(f"[guidance] Cortex Search unavailable ({e.__class__.__name__})")
        return []


def beep():
    subprocess.Popen(["afplay", "/System/Library/Sounds/Sosumi.aiff"])  # non-blocking


def skeleton_png(norm, path, size=480):
    """Skeleton on a blank canvas: no photo of a person ever leaves the laptop."""
    img = np.full((size, size, 3), 255, np.uint8)
    pts = {i: (int(norm[i].x * size), int(norm[i].y * size)) for i in range(len(norm))}
    for a, b in BONES:
        cv2.line(img, pts[a], pts[b], (40, 40, 40), 3)
    for i in {i for bone in BONES for i in bone}:
        cv2.circle(img, pts[i], 5, (40, 40, 220), -1)
    cv2.imwrite(str(path), img)


def ascii_(s):
    return s.encode("ascii", "replace").decode()  # cv2.putText draws ASCII only


def wrap(text, width=60):
    lines, cur = [], ""
    for word in text.split():
        if len(cur) + len(word) + 1 > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return lines + [cur] if cur else lines


def draw(frame, norm, band, trunk, twist, show_deg, ask=None, status="", label=None, risk=None):
    h, w = frame.shape[:2]
    if risk and norm:  # Snowflake ML verdict, beside (never instead of) the REBA band
        r_label, r_prob, r_src = risk
        rc = (180, 60, 200) if r_label == "bad" else (90, 90, 90)
        cv2.rectangle(frame, (10, 80), (330, 130), rc, -1)
        text = f"ML: {'RISKY' if r_label == 'bad' else 'ok'} {r_prob:.2f}" + (" (stub)" if r_src == "stub" else "")
        cv2.putText(frame, text, (22, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    if label:  # labelling mode: make the current label impossible to miss
        lc = COLOURS["green"] if label == "good" else COLOURS["red"]
        cv2.rectangle(frame, (w - 300, 80), (w - 10, 150), lc, -1)
        cv2.putText(frame, f"LABEL: {label.upper()}", (w - 285, 128), cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                    (255, 255, 255), 3)
    col = COLOURS[band]
    if norm:
        pts = {i: (int(p.x * w), int(p.y * h)) for i, p in enumerate(norm)}
        for a, b in BONES:
            cv2.line(frame, pts[a], pts[b], col, 4)
    cv2.rectangle(frame, (0, 0), (w, 70), col, -1)
    msg = {"green": "GOOD POSTURE", "amber": "CAREFUL: BENDING",
           "red": "STOP - USE THE EQUIPMENT IN THE PLAN"}[band] if norm else "STEP INTO VIEW"
    cv2.putText(frame, msg, (20, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)
    if show_deg and norm:
        cv2.putText(frame, f"trunk {trunk:.0f}  twist {twist:.0f}", (20, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    if status:
        cv2.putText(frame, status, (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    if ask:  # Gemma's question panel, answered with keys 1-4
        q, src = ask["data"], ask["source"]
        lines = [f"GEMMA ASKS{' (cached)' if src == 'cache' else ''}:"] + wrap(ascii_(q["question"]))
        lines += [f"  {i + 1}. {ascii_(o)}" for i, o in enumerate(q["options"][:4])]
        top = h - 30 * len(lines) - 30
        cv2.rectangle(frame, (10, top - 10), (w - 10, h - 10), (30, 30, 30), -1)
        for i, line in enumerate(lines):
            cv2.putText(frame, line, (25, top + 22 + 30 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)


def run_debrief(session, task, lang, readings, labels, q):
    """Session-end debrief: summary + Cortex Search guidance -> Gemma, saved for the dashboard."""
    if not readings:
        print("No readings, no debrief.")
        return
    bands = Counter(r["band"] for r in readings)
    worst = max(readings, key=lambda r: r["trunk"])
    summary = {
        "task": task, "readings": len(readings),
        "pct_time": {b: round(100 * n / len(readings)) for b, n in bands.items()},
        "red_alarms": sum(1 for r in readings if r["alarm"]),
        "worst_moment": {"trunk_deg": round(worst["trunk"]), "twist_deg": round(worst["twist"])},
        "trainee_said": [lb["answer"] for lb in labels],
    }
    query = f"{task.replace('_', ' ')} manual handling bending twisting " + " ".join(summary["trainee_said"])
    cites = guidance(query)
    print(f"\nDebrief ({lang}) for session {session}, asking Gemma...")
    try:
        text, src = gemma.debrief(summary, cites, lang)
    except Exception as e:
        print(f"Debrief failed: {e}")
        return
    print(("[cached] " if src == "cache" else "") + text)
    for i, c in enumerate(cites):
        print(f"  [{i + 1}] {c['source']}")
    q.put(("DEBRIEFS", (session, now_adl(), task, lang, json.dumps(summary, ensure_ascii=False), text,
                        json.dumps([c["source"] for c in cites]), src)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="bed_to_chair")
    ap.add_argument("--staff", default="S01", help="anonymous staff code, never a name")
    ap.add_argument("--lang", default="English", help="debrief language, e.g. Nepali, Vietnamese")
    ap.add_argument("--camera", type=int, default=0)
    args = ap.parse_args()

    session = uuid.uuid4().hex[:8]
    snaps = ROOT / "snapshots"
    snaps.mkdir(exist_ok=True)
    q = queue.Queue()
    writer = threading.Thread(target=sink, args=(q,), daemon=True)
    writer.start()
    pool = ThreadPoolExecutor(max_workers=2)  # Gemma calls never block the camera loop
    ml_pool = ThreadPoolExecutor(max_workers=1)  # ML predict (~3.5 s): only the latest reading is scored
    ml_job, risk, prev, recent = None, None, None, []

    opts = vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(MODEL)),
                                        running_mode=vision.RunningMode.VIDEO)
    cam = cv2.VideoCapture(args.camera)
    scorer = reba.Scorer()
    band, trunk, twist, knee = "green", 0.0, 0.0, 180.0
    was_alarm, alarm_in_window, last_sample, show_deg = False, False, 0.0, False
    pending, ask, status, label = None, None, "", None
    readings, labels = [], []
    t0 = time.monotonic()
    print(f"session {session} task={args.task} staff={args.staff} lang={args.lang}")

    with vision.PoseLandmarker.create_from_options(opts) as pose:
        while True:
            ok, frame = cam.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            t = time.monotonic() - t0
            res = pose.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,
                                                 data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), int(t * 1000))
            norm = res.pose_landmarks[0] if res.pose_landmarks else None
            if norm and reba.visible(norm):
                tr_raw, tw_raw, knee = reba.trunk_angles(res.pose_world_landmarks[0])
                trunk, twist, band, alarm = scorer.update(tr_raw, tw_raw, t)
                if alarm and not was_alarm:  # alarm onset
                    beep()
                    snap = snaps / f"{session}_{int(t)}.png"
                    skeleton_png(norm, snap)
                    if pending is None and ask is None:  # one question at a time
                        pending = (pool.submit(gemma.alarm_question, snap, args.task, trunk, twist), trunk, twist)
                        status = "Gemma is looking at the skeleton..."
                was_alarm = alarm
                alarm_in_window |= alarm
            else:
                norm = None

            if pending and pending[0].done():
                fut, a_tr, a_tw = pending
                pending, status = None, ""
                try:
                    data, src = fut.result()
                    ask = {"data": data, "source": src, "trunk": a_tr, "twist": a_tw}
                except Exception as e:
                    print(f"[gemma] question failed: {e}")

            if norm and t - last_sample >= SAMPLE_S:
                q.put(("EVENTS", (session, now_adl(), args.task, round(trunk, 1), round(twist, 1),
                                  round(knee, 1), band, alarm_in_window, args.staff, label)))
                readings.append({"band": band, "trunk": trunk, "twist": twist, "alarm": alarm_in_window})
                last_sample, alarm_in_window = t, False
                recent = (recent + [trunk])[-3:]
                if ml_job is None:  # skip this reading if the previous predict is still running
                    ml_job = ml_pool.submit(ml.ml_risk, ml.features(trunk, twist, knee, prev, recent))
                prev = (trunk, twist)

            if ml_job and ml_job.done():
                try:
                    risk = ml_job.result()
                except Exception:
                    risk = None
                ml_job = None

            draw(frame, norm, band, trunk, twist, show_deg, ask, status, label, risk)
            cv2.imshow("Safe Lift", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("d"):
                show_deg = not show_deg
            if key in (ord("g"), ord("b"), ord("n")):  # labeller marks the lift being performed now
                label = {ord("g"): "good", ord("b"): "bad", ord("n"): None}[key]
            if ask and ord("1") <= key <= ord("4"):
                answer = ask["data"]["options"][key - ord("1")]
                labels.append({"answer": answer})
                q.put(("ALARM_LABELS", (session, now_adl(), args.task, round(ask["trunk"], 1),
                                        round(ask["twist"], 1), ask["data"]["question"], answer, ask["source"])))
                ask = None

    cam.release()
    cv2.destroyAllWindows()
    run_debrief(session, args.task, args.lang, readings, labels, q)
    q.put(None)
    writer.join(timeout=15)
    pool.shutdown(wait=False, cancel_futures=True)
    ml_pool.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    main()
