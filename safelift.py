"""Safe Lift live coach: MediaPipe watches, REBA bands alarm, readings stream to Snowflake.

Run: .venv/bin/python safelift.py --task bed_to_chair --staff S01   (q quits, d toggles degrees)
No Snowflake connection -> rows go to data/events.csv instead.
"""
import argparse
import csv
import queue
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

import reba

ROOT = Path(__file__).parent
MODEL = ROOT / "models" / "pose_landmarker_lite.task"
ADL = ZoneInfo("Australia/Adelaide")
SAMPLE_S = 2.0
COLS = ["session_id", "ts", "task", "trunk_deg", "twist_deg", "knee_deg", "reba_band", "alarm", "staff_code"]
COLOURS = {"green": (60, 180, 75), "amber": (0, 165, 255), "red": (40, 40, 220)}
BONES = [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24), (23, 24),
         (23, 25), (25, 27), (24, 26), (26, 28)]
DDL = """create table if not exists H4H.APP.EVENTS (
  session_id string, ts timestamp_ntz, task string, trunk_deg float, twist_deg float,
  knee_deg float, reba_band string, alarm boolean, staff_code string)"""


def now_adl():
    return datetime.now(ADL).strftime("%Y-%m-%d %H:%M:%S")


def sink(q):
    """Background writer: batch rows to Snowflake every SAMPLE_S, or append to CSV if offline."""
    conn = None
    try:
        import snowflake.connector
        conn = snowflake.connector.connect(connection_name="main")
        conn.cursor().execute(DDL)
        print("[sink] Snowflake H4H.APP.EVENTS")
    except Exception as e:
        print(f"[sink] Snowflake unavailable ({e.__class__.__name__}), writing data/events.csv")
    out = ROOT / "data" / "events.csv"
    out.parent.mkdir(exist_ok=True)
    stop = False
    while not stop:
        rows = []
        try:
            rows.append(q.get(timeout=SAMPLE_S))
            while True:
                rows.append(q.get_nowait())
        except queue.Empty:
            pass
        if None in rows:
            stop = True
            rows = [r for r in rows if r is not None]
        if not rows:
            continue
        if conn:
            try:
                conn.cursor().executemany(
                    f"insert into H4H.APP.EVENTS ({','.join(COLS)}) values ({','.join(['%s'] * len(COLS))})", rows)
                continue
            except Exception as e:
                print(f"[sink] insert failed ({e}), falling back to CSV for this batch")
        new = not out.exists()
        with out.open("a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(COLS)
            w.writerows(rows)
    if conn:
        conn.close()


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


def draw(frame, norm, band, trunk, twist, show_deg):
    h, w = frame.shape[:2]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="bed_to_chair")
    ap.add_argument("--staff", default="S01", help="anonymous staff code, never a name")
    ap.add_argument("--camera", type=int, default=0)
    args = ap.parse_args()

    session = uuid.uuid4().hex[:8]
    snaps = ROOT / "snapshots"
    snaps.mkdir(exist_ok=True)
    q = queue.Queue()
    writer = threading.Thread(target=sink, args=(q,), daemon=True)
    writer.start()

    opts = vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(MODEL)),
                                        running_mode=vision.RunningMode.VIDEO)
    cam = cv2.VideoCapture(args.camera)
    scorer = reba.Scorer()
    band, trunk, twist, knee = "green", 0.0, 0.0, 180.0
    was_alarm, alarm_in_window, last_sample, show_deg = False, False, 0.0, False
    t0 = time.monotonic()
    print(f"session {session} task={args.task} staff={args.staff}")

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
                    skeleton_png(norm, snaps / f"{session}_{int(t)}.png")
                was_alarm = alarm
                alarm_in_window |= alarm
            else:
                norm = None

            if norm and t - last_sample >= SAMPLE_S:
                q.put((session, now_adl(), args.task, round(trunk, 1), round(twist, 1), round(knee, 1),
                       band, alarm_in_window, args.staff))
                last_sample, alarm_in_window = t, False

            draw(frame, norm, band, trunk, twist, show_deg)
            cv2.imshow("Safe Lift", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("d"):
                show_deg = not show_deg

    cam.release()
    cv2.destroyAllWindows()
    q.put(None)
    writer.join(timeout=10)


if __name__ == "__main__":
    main()
