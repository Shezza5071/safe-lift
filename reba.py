"""REBA-style trunk scoring from MediaPipe pose landmarks.

Bands follow REBA trunk thresholds (Hignett and McAtamney 2000):
amber = trunk flexion over 20 deg; red = over 60 deg, or over 20 deg with twist,
sustained for RED_HOLD_S. Indicative only: 2D/monocular pose error is about 5 to 10 deg.
"""
import math
from collections import deque
from statistics import median

# MediaPipe pose landmark indices
L_SHOULDER, R_SHOULDER, L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANKLE, R_ANKLE = 11, 12, 23, 24, 25, 26, 27, 28
CORE = (L_SHOULDER, R_SHOULDER, L_HIP, R_HIP)

AMBER_TRUNK = 20.0
RED_TRUNK = 60.0
TWIST_DEG = 20.0  # calibration knob: shoulder line vs hip line in the floor plane
RED_HOLD_S = 2.0
MIN_VISIBILITY = 0.6
MAX_DEG = 120.0


def _mid(a, b):
    return ((a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2)


def _angle(u, v):
    dot = sum(p * q for p, q in zip(u, v))
    nu = math.sqrt(sum(p * p for p in u))
    nv = math.sqrt(sum(q * q for q in v))
    if nu == 0 or nv == 0:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / (nu * nv)))))


def clamp(deg):
    return max(0.0, min(MAX_DEG, deg))


def visible(norm_landmarks, idx=CORE):
    """Skip frames where the trunk landmarks are not clearly seen."""
    return all(norm_landmarks[i].visibility >= MIN_VISIBILITY for i in idx)


def trunk_angles(world):
    """Trunk flexion, twist and knee angle (deg) from MediaPipe world landmarks (metres, y down)."""
    sh, hp = _mid(world[L_SHOULDER], world[R_SHOULDER]), _mid(world[L_HIP], world[R_HIP])
    trunk = (sh[0] - hp[0], sh[1] - hp[1], sh[2] - hp[2])
    flexion = _angle(trunk, (0.0, -1.0, 0.0))  # up is -y

    # twist: shoulder line vs hip line, projected onto the floor plane (x, z)
    s = (world[R_SHOULDER].x - world[L_SHOULDER].x, world[R_SHOULDER].z - world[L_SHOULDER].z)
    h = (world[R_HIP].x - world[L_HIP].x, world[R_HIP].z - world[L_HIP].z)
    twist = _angle(s, h)

    # knee: hip-knee-ankle on the left leg (180 = straight)
    k, hip, ank = world[L_KNEE], world[L_HIP], world[L_ANKLE]
    knee = _angle((hip.x - k.x, hip.y - k.y, hip.z - k.z), (ank.x - k.x, ank.y - k.y, ank.z - k.z))
    return clamp(flexion), clamp(twist), knee


def raw_band(trunk, twist):
    if trunk > RED_TRUNK or (trunk > AMBER_TRUNK and twist > TWIST_DEG):
        return "red"
    if trunk > AMBER_TRUNK:
        return "amber"
    return "green"


class Scorer:
    """5-frame median smoothing plus the 2 s hold before a red alarm."""

    def __init__(self, window=5):
        self.trunk = deque(maxlen=window)
        self.twist = deque(maxlen=window)
        self.red_since = None

    def update(self, trunk, twist, t):
        """Feed one frame; returns (trunk, twist, band, alarm). alarm is True once red has held RED_HOLD_S."""
        self.trunk.append(trunk)
        self.twist.append(twist)
        tr, tw = median(self.trunk), median(self.twist)
        band = raw_band(tr, tw)
        if band == "red":
            if self.red_since is None:
                self.red_since = t
            if t - self.red_since < RED_HOLD_S:
                band = "amber"  # red not yet sustained
        else:
            self.red_since = None
        return tr, tw, band, band == "red"
