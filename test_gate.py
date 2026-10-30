from pathlib import Path

import pytest

import gate
import gemma

PLANS = sorted((Path(__file__).parent / "demo").glob("plan_*.png"))
GOOD = {"task": "bed_to_chair", "staff_required": 2, "equipment": ["ceiling hoist"], "notes": "No manual lifting."}


def test_check_rules_keeps_contract_keys_only():
    assert gate.check_rules({**GOOD, "extra": 1}) == GOOD


@pytest.mark.parametrize("bad", [
    [GOOD],
    {k: v for k, v in GOOD.items() if k != "equipment"},
    {**GOOD, "staff_required": "2"},
    {**GOOD, "staff_required": True},
    {**GOOD, "staff_required": 0},
    {**GOOD, "equipment": "hoist"},
    {**GOOD, "equipment": [""]},
    {**GOOD, "task": " "},
])
def test_check_rules_rejects_bad_json(bad):
    with pytest.raises(ValueError):
        gate.check_rules(bad)


def test_demo_plans_read_from_cache_offline(monkeypatch):
    """The committed cache is the demo fallback: every sample plan must give valid rules with no network."""
    def offline():
        raise ConnectionError("offline")
    monkeypatch.setattr(gemma, "client", offline)
    monkeypatch.setattr(gemma.time, "sleep", lambda s: None)
    assert len(PLANS) >= 2
    for p in PLANS:
        rules, src = gate.read_plan(p)
        assert src == "cache"
        assert rules["staff_required"] >= 1 and rules["equipment"]
    assert gate.read_plan(PLANS[0])[0]["staff_required"] == 2  # bed_to_chair: hoist + 2 staff
