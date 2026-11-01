# 2026-11-01 — Transformer-style Personalized ISF/ICR Refinement GVU

**Opportunity**: Temporal Transformer attention for extracting invariant, personalized insulin sensitivity factor (ISF) and insulin-to-carb ratio (ICR) directly from CGM + pump history, without hand-tuned heuristics.
**Prototype**: Minimal Generator–Verifier–Updater loop that proposes candidate ISF/ICR, checks against explicit variance + range + hypo-rate criteria, and refines over 2–3 passes.

Base idea draws from recent work on Temporal Fusion Transformers learning patient-specific insulin parameters.

## Run
```bash
python3 gvu_transformer_isf.py
```

See smoke_test.json for the sample run (before/after).
