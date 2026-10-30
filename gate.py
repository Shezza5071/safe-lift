"""Setup gate: Gemma reads a (synthetic) manual handling plan and the room, and blocks the lift until the plan is met.

read_plan returns the plan rules (contract 4 on the map):
{"task": str, "staff_required": int, "equipment": [str], "notes": str}

Run from the repo root to read every demo plan: .venv/bin/python gate.py
"""
import json
import sys
from pathlib import Path

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


if __name__ == "__main__":
    plans = sys.argv[1:] or sorted(str(p) for p in (Path(__file__).parent / "demo").glob("plan_*.png"))
    for p in plans:
        rules, src = read_plan(p)
        print(f"{Path(p).name}{' (cached)' if src == 'cache' else ''}: {json.dumps(rules)}")
