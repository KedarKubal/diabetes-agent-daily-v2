# 2026-11-05: Feature-engineered weekly CGM hypoglycemia risk GVU

Prototype of the Monitoring/Care angle opportunity from Cichosz et al. (2024).

**Underexploited insight**: Explicit feature engineering on LBGI, TBR, CV, GRADE from prior-week CGM yields strong week-ahead excessive-hypoglycemia prediction (AUC 0.83-0.87); the self-improving agent loop can turn raw scores into falsifiable, actionable nudges.

Run: `python3 gvu_hypo.py`

Smoke test on P-1105 (TBR=5.2%, nocturnal): Pass 1 generic nudge fails verifier; Pass 2 specific 15g bedtime carb passes.
