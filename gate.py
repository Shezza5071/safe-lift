"""Setup gate: Gemma reads a (synthetic) manual handling plan and the room, and blocks the lift until the plan is met.

read_plan returns the plan rules (contract 4 on the map):
{"task": str, "staff_required": int, "equipment": [str], "notes": str}
check_room gives Gemma the contract-5 functions (set_checklist, then block_task / allow_task) and returns
{"allowed": bool, "reason": str, "calls": [...], "source": "live" | "cache" | "error"}; no verdict means blocked.

Run from the repo root:
  .venv/bin/python gate.py                        read every demo plan
  .venv/bin/python gate.py room PLAN ROOM [...]   check room photos against a plan (panel previews in snapshots/)
"""
import json
import re
import sys
import textwrap
from pathlib import Path

import cv2
from google.genai import types

import gemma

PLAN_KEYS = {"task": str, "staff_required": int, "equipment": list, "notes": str}

PLAN_PROMPT = """The image is a manual handling plan for moving a care resident (SYNTHETIC, for training).
Extract the rules a trainer must check before the transfer starts.
- task: the transfer task in snake_case, e.g. "bed_to_chair", "sit_to_stand", "chair_to_toilet".
- staff_required: number of staff required for the transfer (integer).
- equipment: every piece of equipment the plan requires, short lowercase names as they would be seen in a room,
  e.g. ["ceiling hoist", "full body sling"]. Empty list if none.
- notes: one short sentence with anything else the trainer must know (e.g. manual lifting not permitted).
Only use what the plan says; do not add equipment it does not list.
JSON: {"task": str, "staff_required": int, "equipment": [str], "notes": str}"""


def check_rules(rules):
    """Returns contract-4 rules with exactly the contract keys, or raises ValueError."""
    if not isinstance(rules, dict):
        raise ValueError(f"plan rules must be an object, got {type(rules).__name__}")
    missing = PLAN_KEYS.keys() - rules.keys()
    if missing:
        raise ValueError(f"plan rules missing {sorted(missing)}")
    for k, t in PLAN_KEYS.items():
        if not isinstance(rules[k], t) or (t is int and isinstance(rules[k], bool)):
            raise ValueError(f"plan rules {k!r} must be {t.__name__}, got {rules[k]!r}")
    if rules["staff_required"] < 1:
        raise ValueError(f"staff_required must be at least 1, got {rules['staff_required']}")
    if not all(isinstance(e, str) and e.strip() for e in rules["equipment"]):
        raise ValueError(f"equipment must be non-empty strings, got {rules['equipment']!r}")
    if not rules["task"].strip():
        raise ValueError("task must not be empty")
    return {k: rules[k] for k in PLAN_KEYS}


def read_plan(image_path):
    """Gemma reads a plan photo. Returns (rules, source); source is "live" or "cache"."""
    rules, src = gemma.gemma_json(PLAN_PROMPT, image_path)
    return check_rules(rules), src


def _declare(name, description, **params):
    schema = types.Schema(type="OBJECT", properties=params, required=list(params)) if params else None
    return types.FunctionDeclaration(name=name, description=description, parameters=schema)


CHECKLIST_TOOLS = [types.Tool(function_declarations=[
    _declare("set_checklist", "Show the trainer the setup checklist, one line per plan requirement with what you see.",
        items=types.Schema(type="ARRAY", items=types.Schema(type="STRING"))),
])]
VERDICT_TOOLS = [types.Tool(function_declarations=[
    _declare("block_task", "Block the lift because the room does not meet the plan.", reason=types.Schema(type="STRING")),
    _declare("allow_task", "Allow the lift because every plan requirement is met."),
])]

ROOM_CONTEXT = """You are the setup gate for a care-worker training lift. The image is the training room.
The resident's manual handling plan requires: {rules}
Training props stand in for the real thing (e.g. a box as the bed, a towel as the slide sheet)."""

CHECKLIST_PROMPT = ROOM_CONTEXT + """
Count the staff: adults standing ready to do the transfer. Look for each item in "equipment" only;
do not add requirements the plan does not list. Call set_checklist with one short line per requirement,
e.g. ["2 staff: 1 seen", "slide sheet: seen"]."""

VERDICT_PROMPT = ROOM_CONTEXT + """
Your checklist for this room: {checklist}
Decide from the checklist only: the requirements are staff_required and the equipment list, nothing else
(the task name and the room's furniture are not requirements). Call block_task with a short reason naming what is missing (e.g. "Plan says 2 staff, 1 seen"),
or allow_task if every requirement is met. If you are unsure, block."""


def _named(calls, name):
    return next((c for c in calls if c["name"] == name), None)


def _staff_seen(checklist):
    """Staff count Gemma reported, from a line like "2 staff: 1 seen"; None if there is no such line."""
    for item in checklist:
        m = re.search(r"staff\D*?(\d+)\s*seen", item, re.I)
        if m:
            return int(m.group(1))
    return None


def check_room(room_image, rules):
    """Gemma checks a room photo against plan rules in two function-calling turns (checklist, then verdict).

    Gemma makes one call per turn, so the verdict turn is given the checklist. Fails closed: no checklist, no verdict,
    any block_task, too few staff in the checklist, or any error means blocked.
    """
    plan = json.dumps(rules)
    try:
        calls, src1 = gemma.gemma(CHECKLIST_PROMPT.format(rules=plan), room_image, tools=CHECKLIST_TOOLS)
        checklist = (_named(calls, "set_checklist") or {"args": {}})["args"].get("items") or []
        if not checklist:
            return {"allowed": False, "reason": "No checklist from Gemma: check the room by hand", "calls": calls,
                    "source": src1}
        verdict, src2 = gemma.gemma(VERDICT_PROMPT.format(rules=plan, checklist=json.dumps(checklist)), room_image,
                                    tools=VERDICT_TOOLS)
    except Exception as e:  # no network and no cache, missing photo, unsupported image type
        return {"allowed": False, "reason": f"Setup check failed: {e}", "calls": [], "source": "error"}
    calls += verdict
    src = "cache" if "cache" in (src1, src2) else "live"
    seen = _staff_seen(checklist)
    if seen is not None and seen < rules["staff_required"]:  # never allow on a staff count below the plan
        return {"allowed": False, "reason": f"Plan says {rules['staff_required']} staff, {seen} seen", "calls": calls,
                "source": src}
    block = _named(verdict, "block_task")
    if block:
        return {"allowed": False, "reason": block["args"].get("reason") or "Plan not met", "calls": calls, "source": src}
    if _named(verdict, "allow_task"):
        return {"allowed": True, "reason": "Plan met", "calls": calls, "source": src}
    return {"allowed": False, "reason": "No verdict from Gemma: check the room by hand", "calls": calls, "source": src}


def _ascii(s):
    return s.encode("ascii", "replace").decode()  # cv2.putText draws ASCII only


def draw_gate_panel(frame, result):
    """Big BLOCKED / READY banner under the posture bar, and Gemma's function calls in a small panel."""
    h, w = frame.shape[:2]
    colour = (60, 180, 75) if result["allowed"] else (40, 40, 220)
    word = "READY" if result["allowed"] else "BLOCKED"
    cached = " (cached)" if result["source"] == "cache" else ""
    cv2.rectangle(frame, (0, 80), (w, 190), colour, -1)
    cv2.putText(frame, f"SETUP: {word}{cached}", (20, 135), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 4)
    cv2.putText(frame, _ascii(result["reason"])[:70], (20, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    lines = ["GEMMA FUNCTION CALLS:"]
    for c in result["calls"]:
        lines += textwrap.wrap(_ascii(f"{c['name']}({json.dumps(c['args'])})"), 48)
    lines = lines[:12]
    left, top = w - 560, h - 26 * len(lines) - 30
    cv2.rectangle(frame, (left - 10, top - 10), (w - 10, h - 10), (30, 30, 30), -1)
    for i, line in enumerate(lines):
        cv2.putText(frame, line, (left, top + 18 + 26 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    return frame


if __name__ == "__main__":
    if sys.argv[1:2] == ["room"]:
        rules, _ = read_plan(sys.argv[2])
        out = Path(__file__).parent / "snapshots"
        out.mkdir(exist_ok=True)
        for room in sys.argv[3:]:
            result = check_room(room, rules)
            print(f"{Path(room).name}: {json.dumps(result)}")
            cv2.imwrite(str(out / f"gate_{Path(room).stem}.png"), draw_gate_panel(cv2.imread(room), result))
    else:
        plans = sys.argv[1:] or sorted(str(p) for p in (Path(__file__).parent / "demo").glob("plan_*.png"))
        for p in plans:
            rules, src = read_plan(p)
            print(f"{Path(p).name}{' (cached)' if src == 'cache' else ''}: {json.dumps(rules)}")
