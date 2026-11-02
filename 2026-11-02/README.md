# 2026-11-02: Week-ahead CGM Hypoglycemia Risk + Specific Nocturnal Carb Nudge (GVU)

## Opportunity
Monitoring/Care angle: Feature-engineered weekly CGM hypo risk (LBGI/TBR/CV) generating specific actionable nocturnal carb nudges, self-improved via GVU loop.

Underexploited insight from Cichosz et al. 2024: The discriminative power of simple engineered CGM features (LBGI, TBR, GRADE) can seed a lightweight self-improving agent that turns abstract risk into concrete bedtime actions, reducing caregiver burden.

## Smoke-test
Sample P-1102 (TBR=5.8%, LBGI=2.1):
- Pass 1: high/90.7 with generic advice → FAILED verifier
- Pass 2: high/90.7 with "15g bedtime carb snack" → PASSED

## Run
```bash
python gvu_hypo.py
```

## Next step
Add real CGM CSV parser and optional LLM critique for richer nudges.
