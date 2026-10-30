"""Check the SYNTHETIC injury registers against the published rates they were calibrated to,
and show the patterns planted in them. Run: python check.py (from this folder or with its path)."""
import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(n):
    with open(HERE / n, newline="") as f:
        return list(csv.DictReader(f))


pat, wrk, res, staff = read("patient_incidents.csv"), read("worker_incidents.csv"), read("residents.csv"), read("staff.csv")
QUARTERS = [(date(y, m, 1), date(y + (m == 10), (m + 3 - 1) % 12 + 1, 1)) for y, m in
            [(2024, 10), (2025, 1), (2025, 4), (2025, 7), (2025, 10), (2026, 1), (2026, 4), (2026, 7)]]


def pct(a, b):
    return f"{100 * a / b:5.1f}%" if b else "  n/a"


print("PATIENT REGISTER")
print(" Quarter      residents  fell   major   (published national Jan-Mar 2025: 31.1% fell, 1.7% major; SA 33.3%, 1.6%)")
for qs, qe in QUARTERS:
    present = {r["resident_id"] for r in res if r["admitted"] < qe.isoformat() and r["discharged_or_period_end"] >= qs.isoformat()}
    falls = [p for p in pat if p["event_type"] in ("fall", "hoist_sling_incident") and qs.isoformat() <= p["datetime_adl"][:10] < qe.isoformat()]
    fell = {p["resident_id"] for p in falls if p["event_type"] == "fall"}
    major = {p["resident_id"] for p in falls if p["qi_major_injury"] == "yes"}
    print(f" {qs:%Y-%m}      {len(present):5}   {pct(len(fell), len(present))} {pct(len(major), len(present))}")

falls = [p for p in pat if p["event_type"] == "fall"]
print(f"\n Falls by activity (published: transfers 41%, walking 36%):")
for k, v in Counter(p["activity"] for p in falls).most_common():
    print(f"   {k:20} {pct(v, len(falls))}")
print(f" Event types: {dict(Counter(p['event_type'] for p in pat))}")
print(f" Severity:    {dict(Counter(p['severity'] for p in pat))}")

print("\nWORKER REGISTER (manual handling incidents only)")
years = 2.0
headcount = len(staff)
serious = [w for w in wrk if w["serious_claim"] == "yes"]
print(f" {len(wrk)} incidents over 2 years, {len(serious)} serious (>= 1 week lost), headcount ~{headcount}")
print(f" Serious manual handling claims per 1,000 workers per year: {1000 * len(serious) / headcount / years:.1f}")
print("   (published, ALL serious claims, community and personal service workers 2023-24p: 19.5 per 1,000;")
print("    body stressing is 47.6% of the nursing, care and support workforce's serious claims -> ~9 per 1,000)")
ag = Counter(w["agency"] for w in wrk)
print(f" People vs objects as the source: {pct(ag['resident'], len(wrk))} residents (published: 54.5% of body stressing claims cite people)")
wk = sorted(float(w["weeks_lost"]) for w in serious)
print(f" Median weeks lost (serious): {wk[len(wk) // 2] if wk else 'n/a'} (published CPSW median 6.6 weeks)")
print(f" Body region: {dict(Counter(w['body_region'] for w in wrk).most_common(3))}")

print("\nPLANTED PATTERNS (a good dashboard or Gemma summary should find these)")
assisted = [p for p in pat if p["staff_assisted"] == "yes" and p["plan_followed"] in ("yes", "no")]
for f in ("yes", "no"):
    grp = [p for p in assisted if p["plan_followed"] == f]
    inj = [p for p in grp if p["severity"] in ("moderate", "major")]
    lw = [p for p in grp if p["linked_worker_incident"]]
    print(f" 1. Plan followed={f:3}: {len(grp):4} assisted events, {pct(len(inj), len(grp))} moderate/major resident injury, {pct(len(lw), len(grp))} also injured a worker")
for sh in ("morning", "afternoon", "night"):
    grp = [p for p in assisted if p["shift"] == sh]
    print(f" 2. {sh:9} shift: {pct(sum(p['plan_followed'] == 'no' for p in grp), len(grp))} of assisted events off-plan; "
          f"{pct(sum('1 present' in p['deviation_detail'] for p in grp), len(grp))} single-staff")
for s in ("Site A", "Site B", "Site C"):
    grp = [p for p in assisted if p["site"] == s]
    print(f" 3. {s}: {pct(sum('not available' in p['deviation_detail'] for p in grp), len(grp))} of assisted events had required equipment unavailable;"
          f" worker incidents {sum(w['site'] == s for w in wrk)}")
sl = [p for p in pat if p["event_type"] == "hoist_sling_incident"]
print(f" 4. Hoist/sling incidents: {len(sl)}, all at {set(p['site'] for p in sl)}, between {min(p['datetime_adl'][:10] for p in sl)} and {max(p['datetime_adl'][:10] for p in sl)}")
new = sum(int(w["tenure_months"]) < 6 for w in wrk)
by_day = [s for s in staff]
print(f" 5. Workers in first 6 months account for {pct(new, len(wrk))} of worker incidents")
wp = [w for w in wrk if w["agency"] == "resident"]
base = sum(p["plan_followed"] == "no" for p in assisted) / len(assisted)
print(f" 1b. Worker people-handling injuries off-plan: {pct(sum(w['plan_followed'] == 'no' for w in wp), len(wp))}"
      f" (vs {100 * base:.1f}% of all assisted resident events off-plan)")
print(f" Roles in worker people-handling injuries: {dict(Counter(w['role'] for w in wp))}")
