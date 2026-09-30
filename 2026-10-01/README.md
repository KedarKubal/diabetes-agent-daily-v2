# 2026-10-01 — Monthly-calibrated PPG + implicit HbA1c

Self-improving GVU slice of Chu et al., *Communications Medicine* (2025):
one monthly pretest + inferred HbA1c feature for wearable PPG glucose.

```
python3 gvu_ppg_monthly_a1c.py
```

Smoke test (synthetic P-088, oral ADD cohort):
- pass 1: pred 115.2 mg/dL, MARD-vs-pretest 18.9% → FAIL
- pass 2: pred 127.8 mg/dL, MARD 10.0% → PASS

Not medical advice.
