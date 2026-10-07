# 2026-10-07 — Awareness-discordance flag

Minimal Generator–Verifier–Updater prototype of Fisher et al. 2025 (Diabetes 74 Suppl 1:366-P): CGM metrics beat Gold/Clarke questionnaires for severe-hypoglycemia discrimination.

Run:

```bash
python discordance_gvu.py
```

Writes `smoke_test.json`. Pass 1 trusts the Gold score and fails. Pass 2 cites two CGM features, sets `risk_band=high_discordance`, and names a concrete clinician action.
