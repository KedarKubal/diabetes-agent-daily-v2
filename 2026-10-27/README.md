# 2026-10-27: Week-ahead CGM Hypoglycemia Risk GVU Prototype

## Opportunity
Monitoring/Care angle from Cichosz et al. (Diabetes Technol Ther 2024): feature-engineered weekly excessive hypoglycemia risk prediction (TBR, LBGI, GRADE, CV, waveform length).

Underexploited insight: these CGM-derived features can seed a lightweight multi-agent loop that not only scores risk but iteratively refines to produce specific, falsifiable care nudges (e.g., nocturnal 15g carb correction).

## GVU Pattern (CS329A)
- **Generator**: Heuristic score from features + flag + initial generic nudge.
- **Verifier**: Explicit criterion — if TBR > 4% then high flag + score >=60 AND specific nudge mentioning carb/basal/nocturnal.
- **Updater**: Feeds critique back; boosts score and specializes nudge.

## Smoke Test
Sample with TBR=5.2%:
- Pass 1: score 75.7 / high / generic nudge → FAIL (needs specific)
- Pass 2: score 85.7 / high / "15g fast-acting carbs if nocturnal..." → PASS

## Run
```bash
python hypo_gvu.py
```
