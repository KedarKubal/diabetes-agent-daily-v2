# 2026-10-28: Weekly CGM Hypoglycemia Risk GVU Prototype

**Opportunity**: Monitoring/Care angle from Cichosz et al. (2024) — feature-engineered ML (LBGI, TBR, GRADE, CV) for week-ahead excessive hypoglycemia prediction (TBR>4%).

**Underexploited insight**: The paper shows these engineered features enable high AUC (0.83-0.87) without complex deep models; a self-improving agent can iteratively refine the risk flag + actionable nocturnal nudge until it meets a falsifiable clinical criterion.

**GVU success criterion**: risk_score >= 70 AND (if prior TBR > 4%) the nudge must contain a specific carb/nocturnal correction.

**Base inspiration**: Minimal slice of feature-based prediction from stanford-hypoglycemia-forecasting style repos, but pure Python heuristic for 2-hour vibe coding.

Run: `python hypo_risk_gvu.py`
