"""Live ML risk flag (map contract 3): score one reading with H4H.APP.LIFT_RISK_MODEL in Snowflake.

ml_risk(features) -> (label, probability_bad, source)
  source "model": the Snowflake classifier answered
  source "stub":  model missing or predict failed, so a rule-based guess (REBA red) stands in
Returns None when Snowflake cannot be reached at all, so the caller hides the badge.
A predict round trip takes ~3.5 s, so call it off the camera loop.
"""
import json

import reba

FEATURES = ["TRUNK_DEG", "TWIST_DEG", "KNEE_DEG", "D_TRUNK", "D_TWIST", "MAX_TRUNK_3"]
SQL = ("select H4H.APP.LIFT_RISK_MODEL!PREDICT(INPUT_DATA => object_construct("
       + ", ".join(f"'{f}', %s" for f in FEATURES) + "))")
_conn = None


def features(trunk, twist, knee, prev, recent_trunk):
    """Contract-2 features from the current reading, the previous one and the last 3 trunk angles."""
    p_trunk, p_twist = prev if prev else (trunk, twist)
    return {"TRUNK_DEG": trunk, "TWIST_DEG": twist, "KNEE_DEG": knee,
            "D_TRUNK": round(trunk - p_trunk, 1), "D_TWIST": round(twist - p_twist, 1),
            "MAX_TRUNK_3": max(recent_trunk)}


def stub(f):
    bad = reba.raw_band(f["TRUNK_DEG"], f["TWIST_DEG"]) == "red"
    return ("bad" if bad else "good"), (1.0 if bad else 0.0), "stub"


def ml_risk(f):
    global _conn
    try:
        if _conn is None:
            import snowflake.connector
            _conn = snowflake.connector.connect(connection_name="main")
    except Exception:
        return None
    try:
        p = json.loads(_conn.cursor().execute(SQL, [round(float(f[k]), 1) for k in FEATURES]).fetchone()[0])
        return p["class"], round(p["probability"]["bad"], 2), "model"
    except Exception:
        return stub(f)


if __name__ == "__main__":  # smoke check: python ml.py
    assert stub(features(75, 5, 150, (40, 4), [40, 75]))[0] == "bad"
    assert stub(features(8, 2, 170, None, [8]))[0] == "good"
    print(ml_risk(features(75, 6, 150, (40, 3), [40, 60, 75])))
