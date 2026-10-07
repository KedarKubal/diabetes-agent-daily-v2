# 2026-10-08 — Composite-outcome DPP closer

Educational prototype of the missing-component closer implied by the JAMA 2025
AI-led vs human-led DPP trial (noninferior on the composite; ~68% still miss it).

## Run

```bash
python3 smoke_test.py
```

Verifier passes only if the draft targets a still-missing composite limb
(weight-loss %, activity minutes, or HbA1c drop), states the computed gap,
gives a numeric action, and names a day-7 check.
