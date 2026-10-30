"""Safe Lift motion graphic. Pillow drawing at 2x, downscaled to 1920x1080, 30 fps.
Usage: python film.py still <scene> <t> out.png   |   python film.py render <scene> out.mp4"""
import math
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

W, H, S, FPS = 1920, 1080, 2, 30
BG = (12, 20, 34)
INK = (238, 242, 247)
MUTED = (140, 152, 170)
LINE = (40, 54, 76)
CARD = (21, 32, 51)
GREEN, AMBER, RED, TEAL = (52, 199, 120), (246, 173, 52), (235, 72, 77), (64, 196, 214)
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-{}.otf"
_fc = {}


def font(size, weight="Bold"):
    k = (size, weight)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FONT.format(weight), int(size * S))
    return _fc[k]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def out_back(x):
    x = clamp(x)
    c = 1.4
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def mix(c, a, bg=BG):
    """colour c at opacity a over the background"""
    return tuple(int(bg[i] + (c[i] - bg[i]) * clamp(a)) for i in range(3))


def appear(t, start, dur=0.5):
    return ease((t - start) / dur)


class Canvas:
    def __init__(self, fade):
        self.im = Image.new("RGB", (W * S, H * S), BG)
        self.d = ImageDraw.Draw(self.im)
        self.fade = fade  # global scene fade (dip to background at the ends)

    def c(self, col, a=1.0, bg=BG):
        return mix(col, a * self.fade, bg)

    def text(self, xy, s, size, col=INK, a=1.0, weight="Bold", anchor="la", bg=BG, dy=0):
        if a <= 0.001:
            return
        x, y = xy
        self.d.text((x * S, (y + dy) * S), s, font=font(size, weight), fill=self.c(col, a, bg), anchor=anchor)

    def rrect(self, box, r, fill=None, outline=None, width=2, a=1.0, bg=BG):
        x0, y0, x1, y1 = box
        self.d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=r * S,
                                 fill=self.c(fill, a, bg) if fill else None,
                                 outline=self.c(outline, a, bg) if outline else None, width=int(width * S))

    def line(self, pts, col, w, a=1.0, bg=BG):
        p = [(x * S, y * S) for x, y in pts]
        self.d.line(p, fill=self.c(col, a, bg), width=int(w * S), joint="curve")
        for x, y in (p[0], p[-1]):
            r = w * S / 2
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=self.c(col, a, bg))

    def dot(self, xy, r, col, a=1.0, bg=BG, outline=None, width=0):
        x, y = xy
        self.d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=self.c(col, a, bg) if col else None,
                       outline=self.c(outline, a, bg) if outline else None, width=int(width * S))

    def arc(self, xy, r, a0, a1, col, w, a=1.0):
        x, y = xy
        self.d.arc([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], a0, a1, fill=self.c(col, a), width=int(w * S))

    def frame(self):
        return self.im.reduce(S)


def tag(cv, t, label, start=0.0):
    a = appear(t, start, 0.4)
    cv.text((120, 92), label.upper(), 22, TEAL, a, "SemiBold")


def source(cv, t, s, start=0.6):
    cv.text((120, 1010), s, 20, MUTED, appear(t, start, 0.6), "Regular")


# ------------------------------------------------------------------ scenes
def s_title(cv, t, d):
    a = appear(t, 0.2, 0.7)
    cv.text((960, 430), "Safe Lift", 150, INK, a, "Black", "mm", dy=(1 - a) * 30)
    b = appear(t, 1.0, 0.6)
    cv.text((960, 560), "A Gemma-coached manual handling trainer for care workers", 40, MUTED, b, "Medium", "mm")
    w = 560 * ease((t - 1.6) / 0.8)
    if w > 1:
        cv.line([(960 - w / 2, 640), (960 + w / 2, 640)], TEAL, 4)
    cv.text((960, 700), "Hack for Humanity Adelaide 2026", 28, TEAL, appear(t, 2.2, 0.6), "SemiBold", "mm")


def s_people(cv, t, d):
    tag(cv, t, "Why it matters in South Australia")
    p = ease((t - 0.4) / 2.2)
    n = int(round(17358 * p))
    cv.text((960, 470), f"{n:,}", 220, INK, appear(t, 0.3, 0.4), "Black", "mm")
    cv.text((960, 640), "South Australians living in residential aged care", 46, INK, appear(t, 2.0, 0.6), "SemiBold", "mm")
    cv.text((960, 712), "Every one of them relies on safe transfers, every day.", 34, MUTED, appear(t, 3.2, 0.6), "Medium", "mm")
    source(cv, t, "Source: AIHW, GEN data: People using aged care by region, 30 June 2025 (Adelaide and Country SA PHNs), via H4H open data.", 1.0)


def s_workers(cv, t, d):
    tag(cv, t, "And for the people doing the lifting")
    for i, (val, unit, line1, line2, start) in enumerate([
            (47.6, "%", "of serious injury claims in Australia's", "nursing, care and support workforce are body stressing", 0.4),
            (21, "%", "of South Australia's body-stressing claims", "come from health care and social assistance", 2.6)]):
        x = 520 + i * 880
        a = appear(t, start, 0.5)
        v = val * ease((t - start) / 1.4)
        s = f"{v:.1f}{unit}" if isinstance(val, float) else f"{int(round(v))}{unit}"
        cv.text((x, 430), s, 170, AMBER if i == 0 else RED, a, "Black", "mm", dy=(1 - a) * 24)
        cv.text((x, 580), line1, 32, INK, appear(t, start + 0.8, 0.5), "SemiBold", "mm")
        cv.text((x, 626), line2, 32, INK, appear(t, start + 0.8, 0.5), "SemiBold", "mm")
    source(cv, t, "Sources: Safe Work Australia, WHS profile: nursing, care and support workforce (average since 2012-13); SafeWork SA, Oct 2024.", 1.2)


def s_insight(cv, t, d):
    tag(cv, t, "What the evidence says")
    a = appear(t, 0.3, 0.6)
    cv.text((960, 400), "Training on its own doesn't prevent back injury.", 62, MUTED, a, "Bold", "mm")
    b = appear(t, 2.0, 0.6)
    cv.text((960, 530), "Higher-order controls come first:", 70, INK, b, "Black", "mm", dy=(1 - b) * 20)
    cv.text((960, 615), "the right equipment, enough staff, and the resident's plan.", 46, INK, appear(t, 2.6, 0.6), "SemiBold", "mm")
    cv.text((960, 720), "So Safe Lift checks the plan before anyone lifts.", 38, TEAL, appear(t, 3.8, 0.6), "SemiBold", "mm")
    source(cv, t, "Sources: Cochrane review CD005958.pub3 (training and advice); Model Code of Practice: Hazardous manual tasks (hierarchy of controls).", 1.0)


def icon_eye(cv, x, y, a):
    cv.d.ellipse([(x - 70) * S, (y - 38) * S, (x + 70) * S, (y + 38) * S], outline=cv.c(TEAL, a, CARD), width=7 * S)
    cv.dot((x, y), 22, TEAL, a, CARD)
    cv.dot((x, y), 9, CARD, a, CARD)


def icon_bubble(cv, x, y, a):
    cv.rrect((x - 72, y - 50, x + 72, y + 34), 22, outline=AMBER, width=7, a=a, bg=CARD)
    cv.line([(x - 30, y + 34), (x - 46, y + 60), (x - 6, y + 34)], AMBER, 7, a, CARD)
    for dx in (-34, 0, 34):
        cv.dot((x + dx, y - 8), 8, AMBER, a, CARD)


def icon_db(cv, x, y, a):
    for k in range(3):
        yy = y - 44 + k * 34
        cv.d.ellipse([(x - 60) * S, (yy - 14) * S, (x + 60) * S, (yy + 14) * S], outline=cv.c(GREEN, a, CARD), width=7 * S)
    cv.line([(x - 60, y - 44), (x - 60, y + 24)], GREEN, 7, a, CARD)
    cv.line([(x + 60, y - 44), (x + 60, y + 24)], GREEN, 7, a, CARD)


def s_how(cv, t, d):
    tag(cv, t, "How it works")
    cards = [(icon_eye, "MediaPipe", "the eyes", ["On-device pose tracking", "Trunk bend and twist, live"]),
             (icon_bubble, "Gemma 4", "the coach", ["Reads the handling plan", "Asks why, then debriefs"]),
             (icon_db, "Snowflake", "the memory", ["Patterns by task and plan,", "never by worker"])]
    for i, (ic, name, role, lines) in enumerate(cards):
        st = 0.4 + i * 0.9
        a = out_back((t - st) / 0.7)
        f = appear(t, st, 0.4)
        x0 = 150 + i * 560
        y0 = 260 + (1 - a) * 60
        cv.rrect((x0, y0, x0 + 500, y0 + 520), 28, fill=CARD, a=f)
        ic(cv, x0 + 250, y0 + 140, f)
        cv.text((x0 + 250, y0 + 270), name, 46, INK, f, "Black", "mm", bg=CARD)
        cv.text((x0 + 250, y0 + 324), role, 32, [TEAL, AMBER, GREEN][i], f, "SemiBold", "mm", bg=CARD)
        for k, ln in enumerate(lines):
            cv.text((x0 + 250, y0 + 400 + k * 42), ln, 27, MUTED, appear(t, st + 0.5, 0.5), "Medium", "mm", bg=CARD)


def person(cv, x, y, a, col=INK, bg=CARD, scale=1.0):
    s = scale
    cv.dot((x, y - 70 * s), 22 * s, col, a, bg)
    cv.line([(x, y - 44 * s), (x, y + 30 * s)], col, 12 * s, a, bg)
    cv.line([(x - 36 * s, y - 20 * s), (x, y - 34 * s), (x + 36 * s, y - 20 * s)], col, 10 * s, a, bg)
    cv.line([(x - 22 * s, y + 90 * s), (x, y + 30 * s), (x + 22 * s, y + 90 * s)], col, 11 * s, a, bg)


def s_gate(cv, t, d):
    tag(cv, t, "Step 1: the setup gate")
    f = appear(t, 0.3, 0.5)
    # plan card
    cv.rrect((120, 200, 760, 860), 28, fill=CARD, a=f)
    cv.text((170, 250), "Manual handling plan", 34, INK, f, "Black", bg=CARD)
    cv.text((170, 300), "Resident R02 (synthetic)", 26, MUTED, f, "Medium", bg=CARD)
    rows = [("Task", "Bed to chair"), ("Method", "Full-body hoist"), ("Staff", "2 required"), ("Manual lift", "Not permitted")]
    for k, (a_, b_) in enumerate(rows):
        r = appear(t, 0.8 + k * 0.25, 0.4)
        y = 380 + k * 100
        cv.line([(170, y + 62), (710, y + 62)], LINE, 2, r, CARD)
        cv.text((170, y), a_, 26, MUTED, r, "Medium", bg=CARD)
        cv.text((710, y), b_, 30, INK, r, "Bold", "ra", bg=CARD)
    cv.text((440, 820), "Gemma reads the plan into rules", 24, AMBER, appear(t, 1.8, 0.5), "SemiBold", "mm", bg=CARD)
    # room card
    cv.rrect((840, 200, 1800, 860), 28, fill=CARD, a=f)
    cv.text((890, 250), "Room check", 34, INK, f, "Black", bg=CARD)
    g = appear(t, 2.2, 0.5)
    # hoist icon
    hx = 1520
    cv.line([(hx - 90, 680), (hx + 90, 680)], MUTED, 12, g, CARD)
    for wx in (hx - 80, hx + 80):
        cv.dot((wx, 697), 12, MUTED, g, CARD)
    cv.line([(hx - 60, 680), (hx - 60, 440)], MUTED, 14, g, CARD)
    cv.line([(hx - 60, 455), (hx + 80, 410)], MUTED, 12, g, CARD)
    cv.line([(hx + 80, 410), (hx + 80, 480)], MUTED, 6, g, CARD)
    cv.line([(hx + 45, 480), (hx + 115, 480)], MUTED, 10, g, CARD)
    cv.text((hx, 745), "hoist", 24, MUTED, g, "Medium", "mm", bg=CARD)
    person(cv, 1080, 560, g)
    second = appear(t, 5.6, 0.5)
    person(cv, 1260, 560 + (1 - second) * 30, second)
    blocked = g * (1 - appear(t, 5.9, 0.3))
    ready = appear(t, 6.0, 0.4)
    if blocked > 0.01:
        cv.rrect((890, 780, 1750, 840), 30, fill=RED, a=blocked, bg=CARD)
        cv.text((1320, 811), "BLOCKED   Plan says 2 staff, 1 seen", 28, INK, blocked, "Black", "mm", bg=mix(RED, blocked * cv.fade, CARD))
    if ready > 0.01:
        cv.rrect((890, 780, 1750, 840), 30, fill=GREEN, a=ready, bg=CARD)
        cv.text((1320, 811), "READY   2 staff and hoist present", 28, BG, ready, "Black", "mm", bg=mix(GREEN, ready * cv.fade, CARD))
    code = appear(t, 3.2, 0.5) * (1 - appear(t, 5.6, 0.3))
    cv.text((890, 320), 'block_task(reason="1 of 2 staff")', 26, AMBER, code, "Medium", bg=CARD)
    code2 = appear(t, 6.2, 0.4)
    cv.text((890, 320), "set_checklist(hoist=True, staff=2)", 26, GREEN, code2, "Medium", bg=CARD)
    cv.text((960, 960), "The lift stays locked until the plan is met.", 34, INK, appear(t, 3.6, 0.6), "SemiBold", "mm")


def s_alarm(cv, t, d):
    tag(cv, t, "Step 2: watch the lift, then ask why")
    f = appear(t, 0.2, 0.5)
    # angle profile over time
    if t < 1.5:
        ang = 8
    elif t < 3.0:
        ang = 8 + 32 * ease((t - 1.5) / 1.2)
    elif t < 3.8:
        ang = 40
    else:
        ang = 40 + 34 * ease((t - 3.8) / 0.8)
    band = RED if ang > 60 else AMBER if ang > 20 else GREEN
    red_since = 4.4
    held = clamp((t - red_since) / 2.0) if ang > 60 else 0
    alarm = t >= red_since + 2.0
    # stage
    cv.rrect((120, 180, 1000, 900), 28, fill=CARD, a=f)
    hip = (520, 600)
    rad = math.radians(ang)
    sh = (hip[0] + 230 * math.sin(rad), hip[1] - 230 * math.cos(rad))
    head = (sh[0] + 62 * math.sin(rad), sh[1] - 62 * math.cos(rad))
    hand = (sh[0] + 30, sh[1] + 150)
    knee = (hip[0] + 18, hip[1] + 140)
    ankle = (hip[0], hip[1] + 270)
    if alarm:
        p = ((t - red_since - 2.0) * 1.6) % 1
        cv.dot(head, 34 + 120 * p, None, 1 - p, CARD, outline=RED, width=6)
    cv.line([(330, 870), (860, 870)], LINE, 4, f, CARD)
    cv.line([hip, knee, ankle], INK, 16, f, CARD)
    cv.line([hip, sh], band, 20, f, CARD)
    cv.line([sh, hand], INK, 14, f, CARD)
    cv.dot(head, 34, INK, f, CARD)
    # bed block the worker reaches toward
    cv.rrect((760, 690, 960, 760), 12, fill=LINE, a=f, bg=CARD)
    cv.text((860, 800), "bed", 22, MUTED, f, "Medium", "mm", bg=CARD)
    # gauge
    gx, gy = 1370, 470
    cv.arc((gx, gy), 230, 180, 360, LINE, 30, f)
    for lo, hi, col in ((0, 20, GREEN), (20, 60, AMBER), (60, 120, RED)):
        cv.arc((gx, gy), 230, 180 + lo * 1.5, 180 + hi * 1.5, mix(col, 0.35, BG), 30, f)
    cv.arc((gx, gy), 230, 180, 180 + ang * 1.5, band, 30, f)
    cv.text((gx, gy - 40), f"{int(ang)}°", 110, band, f, "Black", "mm")
    cv.text((gx, gy + 50), "trunk flexion", 28, MUTED, f, "Medium", "mm")
    label = "RED" if ang > 60 else "AMBER" if ang > 20 else "GREEN"
    cv.text((gx, gy + 100), label, 34, band, f, "Black", "mm")
    # 2 s hold bar
    if ang > 60:
        cv.rrect((1170, 640, 1570, 668), 14, fill=LINE, a=f)
        if held > 0.01:
            cv.rrect((1170, 640, 1170 + 400 * held, 668), 14, fill=RED, a=f)
        cv.text((1370, 700), "held 2 s before alarm" if not alarm else "ALARM", 26, RED if alarm else MUTED, f, "SemiBold", "mm")
    # Gemma question
    q = appear(t, red_since + 2.6, 0.5)
    if q > 0.01:
        cv.rrect((1080, 760, 1840, 930), 24, fill=(45, 38, 24), a=q)
        bgq = mix((45, 38, 24), q * cv.fade)
        cv.text((1110, 785), "Gemma", 24, AMBER, q, "Black", bg=(45, 38, 24))
        cv.text((1110, 825), "Your back was bent past 60\u00b0 for 2 seconds.", 28, INK, q, "SemiBold", bg=(45, 38, 24))
        cv.text((1110, 865), "Were you lifting without the hoist?", 28, INK, q, "SemiBold", bg=(45, 38, 24))
    source(cv, t, "Bands follow REBA trunk thresholds (Hignett & McAtamney 2000). Indicative only.", 1.0)


def s_privacy(cv, t, d):
    tag(cv, t, "Built for a training room")
    items = [("Skeleton only", "No photo of a person leaves the laptop"), ("Nothing recorded", "The camera analyses live and saves no video"),
             ("Consent first", "Everyone in view agrees before it runs")]
    for i, (h, s) in enumerate(items):
        a = appear(t, 0.3 + i * 0.6, 0.5)
        y = 330 + i * 170
        cv.dot((300, y + 30), 16, GREEN, a)
        cv.text((350, y), h, 56, INK, a, "Black", dy=(1 - a) * 16)
        cv.text((350, y + 72), s, 32, MUTED, a, "Medium")


def s_close(cv, t, d):
    a = appear(t, 0.2, 0.7)
    cv.text((960, 400), "Safe Lift", 150, INK, a, "Black", "mm")
    cv.text((960, 530), "Plan first. Then lift.", 56, TEAL, appear(t, 0.9, 0.6), "Bold", "mm")
    cv.text((960, 640), "MediaPipe  ·  Gemma 4  ·  Snowflake  ·  open source (MIT)", 32, MUTED, appear(t, 1.6, 0.6), "Medium", "mm")
    cv.text((960, 700), "Hack for Humanity Adelaide 2026", 30, INK, appear(t, 2.0, 0.6), "SemiBold", "mm")
    cv.text((960, 960), "Training aid only, not a safety device or medical advice. Always follow the resident's plan and your employer's procedures.",
            22, MUTED, appear(t, 2.4, 0.6), "Regular", "mm")


SCENES = [("01_title", s_title, 5.0), ("02_people", s_people, 7.5), ("03_workers", s_workers, 8.0), ("04_insight", s_insight, 6.5),
          ("05_how", s_how, 8.0), ("06_gate", s_gate, 9.5), ("07_alarm", s_alarm, 11.5), ("08_privacy", s_privacy, 5.5),
          ("09_close", s_close, 6.5)]


def draw(fn, t, d):
    fade = min(ease(t / 0.35), ease((d - t) / 0.35))
    cv = Canvas(fade)
    fn(cv, t, d)
    return cv.frame()


def render(name, out):
    _, fn, d = next(s for s in SCENES if s[0] == name)
    n = int(round(d * FPS))
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                          "-pix_fmt", "yuv420p", "-r", str(FPS), out], stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(draw(fn, i / FPS, d).tobytes())
    p.stdin.close()
    sys.exit(p.wait())


if __name__ == "__main__":
    if sys.argv[1] == "still":
        name, t, out = sys.argv[2], float(sys.argv[3]), sys.argv[4]
        _, fn, d = next(s for s in SCENES if s[0] == name)
        draw(fn, t, d).save(out)
    else:
        render(sys.argv[2], sys.argv[3])
