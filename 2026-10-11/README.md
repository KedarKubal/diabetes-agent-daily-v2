# 2026-10-11 — Feature-driven weekly CGM hypo risk + actionable nudge (GVU)

**Opportunity:** Monitoring/Care angle from Cichosz et al. 2024. Underexploited insight: the most discriminative features (LBGI, GRADE, TBR, CV, waveform length) can drive not just a black-box risk score but a self-improving nudge that explicitly targets the top feature.

**Prototype:** Minimal Generator–Verifier–Updater loop that drafts a weekly risk + nudge, verifies against explicit high-risk thresholds (LBGI>1.1 or TBR>4%) and actionability keywords, then revises.

**Smoke test:** P-1111 (elevated LBGI=1.35, TBR=5.2%)  
- Pass 1: generic nudge → failed  
- Pass 2: nocturnal 15g carb correction + basal advice → passed  

Run: `python3 gvu_weekly_hypo.py`
