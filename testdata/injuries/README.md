# Injury registers test set (SYNTHETIC)

Two linked incident registers for a fictional South Australian residential aged care provider: three sites, nine units, 240 beds, 1 October 2024 to 30 September 2026 (eight quarters).

Every resident, worker, incident and dollar figure is invented. The rates are calibrated to published Australian data so that analysis behaves realistically. Do not quote any figure from this set as a finding about real care work.

## Files

| File | Rows | What it holds |
|---|---|---|
| `patient_incidents.csv` | 986 | Resident falls, handling injuries during assisted transfers, and hoist or sling incidents |
| `worker_incidents.csv` | 152 | Worker manual handling incidents: people handling and object handling |
| `residents.csv` | 488 | Residents across the period (with admissions and discharges), mobility category and staff required for transfers |
| `staff.csv` | 299 | Anonymous worker codes, role, employment type and start date |
| `units.csv` | 9 | Beds and hoist numbers per unit |
| `check.py` | | Compares the registers with the published rates and prints the planted patterns |

The two registers link both ways: `patient_incidents.linked_worker_incident` and `worker_incidents.linked_patient_incident` mark events where one transfer injured both a resident and a worker.

## Key fields

**Patient register**
- `event_type`: fall, handling_injury (non-fall injury during an assisted transfer, such as a skin tear or bruise), or hoist_sling_incident.
- `activity`, `transfer_task`, `staff_assisted`.
- Plan compliance: `staff_required`, `staff_present`, `aid_in_plan_used`, `plan_followed`, `deviation_detail`.
- `equipment_fault`.
- Outcome: `severity` (no_injury, minor, moderate, major), `injury_type`, `body_region`, `hospital_transfer`.
- `qi_major_injury`: flags falls with fracture, dislocation, head injury with altered consciousness or subdural haematoma, mirroring the QI Program's major-injury categories. Check the current QI Manual definition before relying on it.

**Worker register**
- `role`, `employment`, `tenure_months`.
- `task`, `agency` (resident or object), `mechanism`.
- `plan_followed`, `body_region`, `nature`.
- Outcome: `severity` (report_only, first_aid, medical_treatment, lost_time), `weeks_lost`, `serious_claim` (one week or more lost, the Safe Work Australia definition), `claim_cost_aud_estimate`.

## Calibration: synthetic vs published

| Measure | This data set | Published figure | Source |
|---|---|---|---|
| Residents who fell, per quarter | 26–33% (average about 30%) | 31.1% national, 33.3% SA (Jan–Mar 2025) | AIHW GEN, Residential Aged Care Quality Indicators, Jan–Mar 2025 |
| Residents with a fall causing major injury, per quarter | 0.7–2.3% (average about 1.7%) | 1.7% national, 1.6% SA | as above |
| Falls during transfers / walking | 45% / 31% | 41% / 36% | Rapp et al. 2012, *JAMDA* 13(2):187.e1-6 (more than 70,000 falls, 528 nursing homes) |
| Worker injuries where people are the source | 58% | 54.5% of body stressing serious claims cite human agencies | Safe Work Australia, WHS profile: nursing, care and support workforce |
| Serious manual handling claims per 1,000 workers a year | 6.7 | About 9 (19.5 all serious claims for community and personal service workers × 47.6% body stressing share) | Safe Work Australia, *Key WHS Statistics Australia 2025* (2023-24p) and the workforce profile |
| Median weeks lost, serious claims | about 11 (only 4 claims) | 6.6 weeks, community and personal service workers | *Key WHS Statistics Australia 2025* |
| Claim cost | log-normal, centred near $12,500 | Median $12,500 CPSW; $19,400 body stressing overall | as above |

**Assumptions with no published Australian base rate, set by judgement:**
- 30% of transfer falls among residents who can move themselves happen during a staff-assisted transfer.
- Rates of non-fall handling injuries (skin tears and bruising during transfers).
- About 75% of worker incidents are reported without time lost.
- About 2–3% of assisted transfer incidents also injure a worker when the plan is followed, against about 10% when it isn't.

The serious-claim count is small (4 in two years), as it would be for a 240-bed provider. Expect it to vary between seeds.

## Planted patterns

A good dashboard, analysis or Gemma summary should find these.

1. **Plan not followed → more harm.** Off-plan assisted transfers have about three times the rate of moderate or major resident injury (29.5% vs 10.5%). Off-plan transfers also make up 29.5% of worker people-handling injuries, against 17.3% of assisted events overall.
2. **Night shift.** Off-plan transfers nearly double at night (26% vs 14–15%), driven by single-staff transfers (18% vs 2–5%).
3. **Site C equipment shortage.** Site C's general and high care units are short of ceiling hoists, so "required equipment not available" is more common there.
4. **Hoist and sling cluster.** Site B has four sling incidents between March and April 2026: two detachments from the spreader bar hook, a wrong sling size and an incompatible third-party sling. One resident fell with a hip fracture. This mirrors the failure modes in the UK MHRA National Patient Safety Alert on hoists and slings (NatPSA/2026/005/MHRA, 16 September 2026).
5. **New starters.** Workers in their first six months account for about 40% of worker manual handling incidents.

## Sources

- AIHW GEN, Residential Aged Care Quality Indicators, January to March 2025: https://www.gen-agedcaredata.gov.au/getmedia/4a2e5243-0eff-4a9d-b836-355dd777c7c4/RACS-QI-report-January-to-March-2025-previous-releases
- Department of Health, Disability and Ageing, National Aged Care Quality Indicator Program Manual: https://www.health.gov.au/sites/default/files/2025-10/national-aged-care-quality-indicator-program-manual-part-a.pdf
- Rapp K, Becker C, Cameron ID, König HH, Büchele G (2012). Epidemiology of falls in residential aged care. *JAMDA* 13(2):187.e1-6: https://pubmed.ncbi.nlm.nih.gov/21816682/
- Robinovitch SN et al. (2013). Video capture of the circumstances of falls in elderly people residing in long-term care. *The Lancet* 381(9860):47-54
- Safe Work Australia, Key Work Health and Safety Statistics Australia 2025: https://data.safeworkaustralia.gov.au/sites/default/files/2025-10/Key_Work_Health_and_Safety_Statistics_Australia_2025.pdf
- Safe Work Australia, WHS profile: nursing, care and support workforce: https://data.safeworkaustralia.gov.au/profile/whs-profile-nursing-care-support-workforce
- SafeWork SA, Campaign to combat body stressing claims (21 October 2024): https://www.safework.sa.gov.au/news-and-alerts/news/news/2024/campaign-to-combat-body-stressing-claims
- MHRA, NatPSA/2026/005/MHRA, Patient hoists and slings: https://www.gov.uk/drug-device-alerts/national-patient-safety-alert-patient-hoists-and-slings-all-types-risk-of-death-and-serious-harm-from-falls-natpsa-slash-2026-slash-005-slash-mhra
