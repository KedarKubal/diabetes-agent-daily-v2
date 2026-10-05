# 2026-10-06 — Context-Horizon Hypoglycemia Gate

Opportunity: Quader et al. 2025 showed CGM ML hypo prediction improves beyond 30 min only when insulin, carbohydrate, and activity are inputs, and that false positives must be judged against the patient's daily hypo risk profile.

Run: `python3 gvu_hypo_gate.py`

Smoke P-718: pass 1 failed (slope-only, no 15 g action); pass 2 passed (IOB + carb residual + MET, 15 g correction).

Not a medical device.
