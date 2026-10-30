# Evidence pack

Sources for the pitch, README and final slide. Checked 30 Oct 2026, 6:30pm ACDT. Each line says what the source supports and what it does not.

## Pitch numbers (use these)

| Claim (as said in the demo) | Source | Checked |
|---|---|---|
| Body stressing is **47.6%** of serious claims in Australia's nursing, care and support workforce (average since 2012-13). | Safe Work Australia, *WHS profile: nursing, care and support workforce* (May 2025). [Profile](https://data.safeworkaustralia.gov.au/profile/whs-profile-nursing-care-support-workforce) · [PDF](https://data.safeworkaustralia.gov.au/sites/default/files/2025-05/Nursing_care_support_workforce_WHS_profile_May2025.pdf) | Yes |
| In 2022-23, **54.5%** of those body stressing claims involved another person as the direct cause (the person being moved). | Same profile. | Yes |
| In SA, health care and social assistance workers are **21%** of body stressing claims, the most of any industry (manufacturing 17%, construction 10%). SA had **6,035** body stressing claims in 2023. | SafeWork SA, *Campaign to combat body stressing claims*, 21 Oct 2024. [Link](https://www.safework.sa.gov.au/news-and-alerts/news/news/2024/campaign-to-combat-body-stressing-claims) | Yes, from the release text as indexed. The page blocks scripted access, so open it once by hand before quoting on a slide. Say "health care and social assistance", not "health care workers". |
| **17,358** South Australians were living in residential aged care at 30 June 2025 (plus 28,006 on home care packages). | AIHW GEN Aged Care Data, via H4H Snowflake `H4H.HEALTH` (Sapna, comment on #11). | From Sapna's query. Context only. |

## Supporting research (from the Researcher, checked against the papers)

- **Victorian nurses and midwives (Brusco et al. 2025).** Musculoskeletal compensation claims (2017-2021) cost about **$14.3 million a year** in lost work (AUD 14,325,109). At two Victorian health services, **748** staff musculoskeletal incidents happened while staff were helping move patients, and **60%** involved the trunk. That is the body part Safe Lift scores.
  Brusco N, Guerbaai R, Graven C, Taylor N, Hill K, Ekegren C. Deriving insights from an occupational incident reporting system to enhance understanding of musculoskeletal incidents among nurses and midwives. *Nurs Open*. 2025;12(12):e70359. [doi:10.1002/nop2.70359](https://doi.org/10.1002/nop2.70359)
- **Real-time posture feedback works better than a workshop (UPRISE, Soni et al. 2024).** In a Melbourne paediatric surgery pilot, surgeons wore a device that vibrated when they slouched. Their time in high-risk posture fell from **50.0% to 20.7%** (p = 0.005). Surgeons given an education workshop instead got *worse* (47.5% to 67.8%). Limits: 8 surgeons, 100 procedures, surgeons not carers, vibration not a screen alarm. Use it as "supports investigating", not proof.
  Soni S, Ritchie A, Liu S, Pacilli M, Nataraja R. Using wearable technology for Posture Regulation to Improve Surgical Ergonomics in the paediatric operating room: the UPRISE trial: a pilot study. *Surg Endosc*. 2024;38(8):4445-4456. [doi:10.1007/s00464-024-10933-5](https://doi.org/10.1007/s00464-024-10933-5)
- **Training alone does not prevent back pain.** Cochrane review of manual handling advice and training ([link](https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.CD005958.pub3/information), from PLAN.md, not re-checked today). This is why the setup gate (follow the plan, use the equipment) leads the demo, not "bend your knees".

### Suggested pitch paragraph

> Body stressing causes nearly half of serious injury claims in Australia's care workforce (47.6%), and in SA health care and social assistance has the most body stressing claims of any industry. In Victoria, these injuries cost about $14.3 million a year in lost work for nurses and midwives, and 60% of staff incidents during patient moves involve the trunk. Workshops alone don't change posture, but in one pilot real-time feedback cut time in high-risk posture by more than half. Safe Lift puts the plan check and that live feedback into training.

## Trainer quote

**Not obtained.** No SA Certificate III trainer or facility educator was reachable before the freeze. Do not use an invented or paraphrased quote. If one arrives, add it here with name, role, organisation and consent to be quoted.

## Credit lines (README and final slide)

**Data**
- Based on: Australian Institute of Health and Welfare, GEN Aged Care Data, People using aged care by region 2024-25. CC BY 4.0. (H4H set A2; we summarised it to SA totals.)

**Guidance (loaded into Cortex Search)**
- Safe Work Australia, *Model Code of Practice: Hazardous manual tasks*. https://www.safeworkaustralia.gov.au/doc/model-code-practice-hazardous-manual-tasks
- Safe Work Australia, *Lifting, pushing and pulling (manual tasks)*. https://www.safeworkaustralia.gov.au/safety-topic/hazards/lifting-pushing-and-pulling-manual-tasks
- WorkSafe Victoria, *Transferring people safely* and *Transferring people from beds and chairs*. https://www.worksafe.vic.gov.au/resources/transferring-people-safely-handbook-workplaces
- SafeWork NSW, *Aged care*. https://www.safework.nsw.gov.au/your-industry/health-care-and-social-assistance/aged-care

**Methods and models**
- REBA: Hignett S, McAtamney L. Rapid Entire Body Assessment (REBA). *Applied Ergonomics*. 2000;31(2):201-205.
- Gemma 4 (`gemma-4-26b-a4b-it`), [Gemma terms](https://ai.google.dev/gemma/terms). MediaPipe Pose Landmarker, Apache 2.0.

**Statistics**
- Safe Work Australia, WHS profile: nursing, care and support workforce (May 2025).
- SafeWork SA, Campaign to combat body stressing claims (21 Oct 2024).
- Brusco et al. 2025 and Soni et al. 2024, as cited above.

## Limits to say out loud

- H4H open data has no posture or lift data, so the aged care number is context, not a measure of Safe Lift.
- Safe Lift is a training aid. None of these sources shows that Safe Lift prevents injuries.
