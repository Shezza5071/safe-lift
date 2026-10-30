import math
from types import SimpleNamespace as P

import reba


def lm(x, y, z=0.0, v=1.0):
    return P(x=x, y=y, z=z, visibility=v)


def body(lean_deg=0.0, twist=False):
    """33 world landmarks: hips at origin, trunk leaning forward (towards -z) by lean_deg."""
    pts = [lm(0, 0) for _ in range(33)]
    a = math.radians(lean_deg)
    up, fwd = -0.5 * math.cos(a), -0.5 * math.sin(a)
    pts[reba.L_HIP], pts[reba.R_HIP] = lm(-0.1, 0), lm(0.1, 0)
    if twist:  # shoulders rotated ~45 deg in the floor plane
        pts[reba.L_SHOULDER], pts[reba.R_SHOULDER] = lm(-0.14, up, fwd - 0.14), lm(0.14, up, fwd + 0.14)
    else:
        pts[reba.L_SHOULDER], pts[reba.R_SHOULDER] = lm(-0.2, up, fwd), lm(0.2, up, fwd)
    pts[reba.L_KNEE], pts[reba.L_ANKLE] = lm(-0.1, 0.45), lm(-0.1, 0.9)
    return pts


def test_upright_is_green():
    tr, tw, knee = reba.trunk_angles(body(0))
    assert tr < 5 and tw < 5 and knee > 175
    assert reba.raw_band(tr, tw) == "green"


def test_bands():
    assert reba.raw_band(*reba.trunk_angles(body(40))[:2]) == "amber"
    assert reba.raw_band(*reba.trunk_angles(body(70))[:2]) == "red"
    assert reba.raw_band(*reba.trunk_angles(body(30, twist=True))[:2]) == "red"


def test_clamp_and_visibility():
    assert reba.clamp(166) == reba.MAX_DEG and reba.clamp(-3) == 0
    pts = body(0)
    pts[reba.L_HIP].visibility = 0.3
    assert not reba.visible(pts)


def test_red_needs_two_seconds_and_median_drops_spikes():
    s = reba.Scorer()
    assert s.update(70, 0, 0.0)[2] == "amber"   # red not yet held
    assert s.update(70, 0, 1.0)[3] is False
    assert s.update(70, 0, 2.1)[3] is True       # held 2 s -> alarm
    s = reba.Scorer()
    for t in range(4):
        s.update(5, 0, t)
    assert s.update(120, 0, 5)[2] == "green"     # one-frame spike filtered by median
