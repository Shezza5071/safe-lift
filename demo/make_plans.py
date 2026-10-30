"""Renders the SYNTHETIC manual handling plan images Gemma reads in the demo (demo/plan_*.png).

Run from the repo root: .venv/bin/python demo/make_plans.py
Content follows testdata/plans_text (R01, R05, R12), one transfer task per plan.
plan_demo_two_staff matches the demo room photos (demo/room_*.jpg): a box as the bed, no hoist or slide sheet.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent
FONT = "/System/Library/Fonts/Helvetica.ttc"

PLANS = {
    "plan_demo_two_staff": ("R13", "Bed to chair", [
        ("Staff required", "2"),
        ("Equipment", "None"),
        ("Method", "Assisted transfer with 2 staff. Never attempt with 1 staff."),
        ("Mobility", "Partially cooperative; partial weight bearing"),
        ("Notes", "Explain each step before moving."),
    ]),
    "plan_bed_to_chair": ("R01", "Bed to chair", [
        ("Staff required", "2"),
        ("Equipment", "Ceiling hoist, full body sling"),
        ("Method", "Full body hoist transfer. Manual lifting is NOT permitted."),
        ("Mobility", "Non cooperative; no weight bearing"),
        ("Notes", "Dense right hemiplegia; no weight bearing."),
    ]),
    "plan_sit_to_stand": ("R05", "Sit to stand", [
        ("Staff required", "2"),
        ("Equipment", "Standing hoist, slide sheet"),
        ("Method", "Standing hoist. Manual lifting is NOT permitted."),
        ("Mobility", "Partially cooperative; partial weight bearing"),
        ("Notes", "Parkinson's freezing; use verbal cueing."),
    ]),
    "plan_chair_to_toilet": ("R12", "Chair to toilet", [
        ("Staff required", "1"),
        ("Equipment", "Sit to stand aid, walking frame"),
        ("Method", "Sit to stand aid, then walking frame. Manual lifting is NOT permitted."),
        ("Mobility", "Partially cooperative; partial weight bearing"),
        ("Notes", "Good upper body strength."),
    ]),
}


def font(size, bold=False):
    return ImageFont.truetype(FONT, size, index=1 if bold else 0)


def render(resident, task, rows):
    img = Image.new("RGB", (1000, 760), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 999, 90], fill=(20, 60, 110))
    d.text((40, 22), "MANUAL HANDLING PLAN", font=font(40, True), fill="white")
    d.text((40, 110), "SYNTHETIC - training use only, not a real resident", font=font(24, True), fill=(200, 0, 0))
    d.text((40, 160), f"Resident: {resident}        Task: {task}", font=font(30, True), fill="black")
    y = 230
    for label, value in rows:
        d.line([40, y - 12, 960, y - 12], fill=(200, 200, 200), width=2)
        d.text((40, y), label, font=font(26, True), fill=(60, 60, 60))
        d.text((300, y), value, font=font(26), fill="black")
        y += 80
    d.text((40, 690), "Review due: 2026-12-01", font=font(22), fill=(90, 90, 90))
    return img


if __name__ == "__main__":
    for name, (resident, task, rows) in PLANS.items():
        render(resident, task, rows).save(OUT / f"{name}.png")
        print(f"wrote demo/{name}.png")
