# 2026-11-18 — Self-Improving Hypoglycemia Risk Flag (GVU)

**Opportunity:** Monitoring/Care angle — multi-task joint forecasting + hypo classification insight from DA-CMTL style papers, prototyped as critique-driven specificity for nocturnal risk.

**Base idea:** Fork of Glycemic-Sentinel style multi-agent, minimal pure-Python GVU.

**Verifier criterion:** For nocturnal + slope < -1 + TBR > 4: must output HIGH risk (>=70) AND specific 15g carb bedtime nudge.

**Smoke test result:** Pass 1 failed on generic nudge; Pass 2 revised to specific 15g carb and passed.

See `gvu_hypo_risk_agent.py` and `smoke_test_result.json`.
