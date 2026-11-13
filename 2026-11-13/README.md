# 2026-11-13 Daily Diabetes Agent

## Opportunity Prototyped
Monitoring/Care angle: Agentic multimodal personalized hypoglycemia risk flag + specific actionable nudge (inspired by GlucoAgent / DiabAgent papers).

## GVU Loop
- Generator: Produces risk level/score + nudge from CGM features (TBR, slope, nocturnal).
- Verifier: Explicit criterion — for high nocturnal risk (TBR>4%, negative slope, nocturnal), must be high score >=70 and nudge contain explicit 15g carb correction.
- Updater: Feeds critique back; loops until pass or max 3.

## Smoke Test
Ran on sample P-1113 (TBR=5.8%, slope=-1.2, nocturnal). Pass 1 failed (generic nudge); Pass 2 passed with specific 15g correction.

Run: `python3 gvu_diabetes_agent.py`
