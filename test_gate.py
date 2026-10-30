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
    rules = {}
    for p in PLANS:
        rules[p.stem], src = gate.read_plan(p)
        assert src == "cache"
        assert rules[p.stem]["staff_required"] >= 1
        assert rules[p.stem]["equipment"] or p.stem == "plan_demo_two_staff"  # only the demo plan needs none
    assert rules["plan_bed_to_chair"]["staff_required"] == 2  # the demo plan: hoist + 2 staff


@pytest.mark.parametrize("path, kind", [("demo/room_1.jpg", "image/jpeg"), ("x.JPEG", "image/jpeg"),
                                        ("snap.png", "image/png"), ("p.webp", "image/webp")])
def test_image_type_follows_extension(path, kind):
    assert gemma.mime(path) == kind


def test_unsupported_image_type_fails_early():
    with pytest.raises(ValueError):
        gemma.mime("plan.pdf")


def _offline(monkeypatch):
    def offline():
        raise ConnectionError("offline")
    monkeypatch.setattr(gemma, "client", offline)
    monkeypatch.setattr(gemma.time, "sleep", lambda s: None)


@pytest.mark.parametrize("room, allowed", [("room_1.jpg", False), ("room_2.jpg", True)])
def test_demo_rooms_gate_from_cache_offline(monkeypatch, room, allowed):
    """Demo fallback: 1 person blocks the 2-staff plan, 2 people allow it, with no network."""
    _offline(monkeypatch)
    demo = Path(__file__).parent / "demo"
    rules, _ = gate.read_plan(demo / "plan_demo_two_staff.png")
    result = gate.check_room(demo / room, rules)
    assert result["allowed"] is allowed and result["source"] == "cache"
    assert [c["name"] for c in result["calls"]][0] == "set_checklist"


@pytest.mark.parametrize("verdict, allowed, reason", [
    ([{"name": "allow_task", "args": {}}], True, "Plan met"),
    ([{"name": "block_task", "args": {"reason": "Plan says 2 staff, 1 seen"}}], False, "Plan says 2 staff, 1 seen"),
    ([], False, "No verdict from Gemma: check the room by hand"),
    ([{"name": "allow_task", "args": {}}, {"name": "block_task", "args": {"reason": "No hoist"}}], False, "No hoist"),
])
def test_check_room_verdicts_fail_closed(monkeypatch, verdict, allowed, reason):
    replies = iter([([{"name": "set_checklist", "args": {"items": ["2 staff: 2 seen"]}}], "live"), (verdict, "live")])
    monkeypatch.setattr(gemma, "gemma", lambda *a, **k: next(replies))
    result = gate.check_room("room.jpg", GOOD)
    assert (result["allowed"], result["reason"]) == (allowed, reason)


def test_check_room_blocks_when_gemma_unavailable(monkeypatch):
    def down(*a, **k):
        raise RuntimeError("Gemma failed after 3 tries")
    monkeypatch.setattr(gemma, "gemma", down)
    result = gate.check_room("room.jpg", GOOD)
    assert result["allowed"] is False and result["source"] == "error"


def test_draw_gate_panel_draws_on_frame():
    import numpy as np
    frame = np.zeros((720, 1280, 3), np.uint8)
    gate.draw_gate_panel(frame, {"allowed": False, "reason": "Plan says 2 staff, 1 seen", "source": "cache",
                                 "calls": [{"name": "block_task", "args": {"reason": "x"}}]})
    assert frame[100, 10].tolist() == [40, 40, 220]  # red banner


def test_check_room_blocks_on_low_staff_count_even_if_gemma_allows(monkeypatch):
    replies = iter([([{"name": "set_checklist", "args": {"items": ["2 staff: 1 seen"]}}], "live"),
                    ([{"name": "allow_task", "args": {}}], "live")])
    monkeypatch.setattr(gemma, "gemma", lambda *a, **k: next(replies))
    result = gate.check_room("room.jpg", GOOD)
    assert (result["allowed"], result["reason"]) == (False, "Plan says 2 staff, 1 seen")


def test_check_room_blocks_without_checklist(monkeypatch):
    replies = iter([([], "live"), ([{"name": "allow_task", "args": {}}], "live")])
    monkeypatch.setattr(gemma, "gemma", lambda *a, **k: next(replies))
    assert gate.check_room("room.jpg", GOOD)["allowed"] is False


def test_check_room_blocks_on_missing_photo():
    result = gate.check_room("demo/no_such_room.jpg", GOOD)
    assert result["allowed"] is False and result["source"] == "error"
