# 2026-11-14: Multimodal Wearable Prediabetes Risk Screener GVU

**Opportunity**: Diagnostics/Biosensors — early prediabetes detection via noninvasive smartwatch digital biomarkers (HRV, activity variance, skin temp, sleep).

**Underexploited insight**: Personalized models from multimodal wearable streams (as in 2021 npj Digital Medicine) outperform population averages; a self-improving GVU agent can iteratively refine risk flags and actionable nudges against explicit clinical heuristics.

**Verifier success criterion**: Score ∈ [0,1]; for high-risk features (HRV <35 or activity_var >0.4) require score ≥0.6 AND specific/actionable nudge (walk/breathing/clinician); otherwise fail and critique.

**Base**: Pure Python heuristic agents (no external LLM) for 2-hour vibe coding. Fork-friendly minimal structure.

**Smoke test**: High-risk sample (HRV=25, act_var=0.6) → pass1: score 0.85 / high / specific nudge → passed.

Run: `python3 gvu_prediabetes_wearable.py`
