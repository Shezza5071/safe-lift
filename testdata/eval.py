"""Safe Lift evaluation on the SYNTHETIC test set.

Put this folder inside the safe-lift repo (as testdata/) and run from the repo root:
    .venv/bin/python testdata/eval.py
Optional, once Gemma has produced outputs:
    .venv/bin/python testdata/eval.py --gemma testdata/gemma_predictions.csv --gate testdata/gate_predictions.csv

It reports:
  1. Alarm accuracy of reba.Scorer (the live alarm) against the known right answer per session.
  2. Agreement between the two human raters on each DINO item (Cohen's kappa).
  3. If supplied, agreement between Gemma's DINO suggestions and rater A, and Gemma's setup-gate accuracy.
"""
import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the repo root, so `import reba` uses the real scoring code
import reba  # noqa: E402

UNSAFE = {"D_stoop_lift", "E_twist_pivot", "H_occlusion"}  # truly unsafe lifts, whatever the camera saw


def read(name):
    with open(HERE / name, newline="") as f:
        return list(csv.DictReader(f))


def kappa(x, y):
    pairs = [(a, b) for a, b in zip(x, y) if a != "" and b != ""]
    if not pairs:
        return None, 0
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return (1.0 if po == 1 else 0.0) if pe == 1 else (po - pe) / (1 - pe), n


def norm(v):
    return "" if v in ("", None) else f"{float(v):g}"


def alarm_eval(sessions):
    frames = defaultdict(list)
    for r in read("frames_10hz.csv"):
        frames[r["session_id"]].append(r)
    print("\n1. LIVE ALARM (reba.Scorer, frames with visibility < 0.6 skipped as the app does)")
    tp = fp = fn = tn = 0
    rows = []
    for s in sessions:
        if s["expected_gate"] == "block":
            continue
        sc, fired, first = reba.Scorer(), False, None
        for f in frames[s["session_id"]]:
            if float(f["visibility"]) < reba.MIN_VISIBILITY:
                continue
            *_, alarm = sc.update(float(f["trunk_deg"]), float(f["twist_deg"]), float(f["t_s"]))
            if alarm and not fired:
                fired, first = True, f["t_s"]
        exp = s["expected_alarm"]
        unsafe = s["scenario"] in UNSAFE
        if exp != "either":
            tp += fired and unsafe
            fp += fired and not unsafe
            fn += (not fired) and unsafe
            tn += (not fired) and not unsafe
        ok = {"yes": fired, "no": not fired, "no_missed": not fired, "either": True}[exp]
        rows.append((s["session_id"], s["scenario"], exp, "ALARM" if fired else "-", first or "", "ok" if ok else "MISMATCH"))
    for r in rows:
        print("   {:5} {:22} expected={:9} got={:5} first_alarm_s={:5} {}".format(*r))
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    print(f"   Against truly unsafe lifts: TP={tp} FP={fp} FN={fn} TN={tn}  precision={prec:.2f} recall={rec:.2f}")
    print("   (Occlusion sessions are unsafe but invisible to the camera, so they count as misses by design;"
          " borderline sessions are excluded.)")
    return sum(r[-1] == "MISMATCH" for r in rows)


def dino_eval(sessions, gemma_path):
    ratings = read("dino_ratings.csv")
    items = [k for k in ratings[0] if k not in ("session_id", "rater", "total_0_16")]
    by = {(r["session_id"], r["rater"]): r for r in ratings}
    sids = [s["session_id"] for s in sessions if s["expected_gate"] == "allow"]
    print("\n2. DINO INTER-RATER AGREEMENT (rater A vs rater B, Cohen's kappa, unweighted)")
    ks = []
    for it in items:
        xa, xb = [norm(by[(s, "A")][it]) for s in sids], [norm(by[(s, "B")][it]) for s in sids]
        k, n = kappa(xa, xb)
        agree = sum(a == b for a, b in zip(xa, xb)) / len(xa)
        ks.append(k)
        print(f"   {it:30} kappa={k:5.2f}  agreement={agree:4.0%}  n={n}")
    print(f"   Mean kappa {sum(ks) / len(ks):.2f}  (published DINO validation reported > 0.75 per item)")
    print("   Note: kappa drops towards 0 when nearly every answer is the same (e.g. staffing is almost always"
          " adequate once the setup gate has passed), so read it alongside percent agreement.")
    if gemma_path:
        g = {r["session_id"]: r for r in csv.DictReader(open(gemma_path, newline=""))}
        print("\n3a. GEMMA DINO SUGGESTIONS vs rater A")
        for it in items:
            xs = [norm(by[(s, "A")][it]) for s in sids if s in g]
            ys = [norm(g[s].get(it, "")) for s in sids if s in g]
            k, n = kappa(xs, ys)
            print(f"   {it:30} " + (f"kappa={k:5.2f}  n={n}" if k is not None else "no predictions"))


def gate_eval(sessions, gate_path):
    if not gate_path:
        return
    g = {r["session_id"]: r["gate"].strip().lower() for r in csv.DictReader(open(gate_path, newline=""))}
    print("\n3b. GEMMA SETUP GATE (allow / block) vs expected")
    right = sum(g.get(s["session_id"]) == s["expected_gate"] for s in sessions if s["session_id"] in g)
    wrong = [(s["session_id"], s["expected_gate"], g[s["session_id"]]) for s in sessions
             if s["session_id"] in g and g[s["session_id"]] != s["expected_gate"]]
    print(f"   {right}/{len(g)} correct")
    for w in wrong:
        print("   wrong: {} expected {} got {}".format(*w))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gemma", help="CSV in the gemma_predictions_TEMPLATE.csv format, filled in")
    ap.add_argument("--gate", help="CSV with columns session_id,gate (allow/block)")
    a = ap.parse_args()
    sessions = read("sessions.csv")
    print(f"SYNTHETIC test set: {len(sessions)} sessions, {Counter(s['scenario'] for s in sessions)}")
    bad = alarm_eval(sessions)
    dino_eval(sessions, a.gemma)
    gate_eval(sessions, a.gate)
    print(f"\nAlarm mismatches against the expected answers: {bad}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
