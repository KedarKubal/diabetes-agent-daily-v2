# 2026-11-21: GVU Hypoglycemia Risk Flag from CGM Trends

## Opportunity
Monitoring/Care angle: Multi-day CGM residual patterns (slope + low-count density) for proactive hypo flags before clinical threshold.

Underexploited insight from papers on reliability-aware digital twins and multitask hypo forewarning: simple residual trend heuristics can seed self-improving agents that refine risk labels against explicit clinical criteria (e.g., <55 mg/dL or ≥3 lows in 30 min).

## Verifier Success Criterion
Flag "high" if any recent glucose <55 OR ≥3 readings <70 in last 30 min; otherwise prefer lower risk to avoid alert fatigue. Loop is falsifiable.

## Files
- gvu_hypo_nudge.py: Generator (heuristic score/slope/lows) → Verifier → Updater loop (2-3 passes, logs changes).
- Smoke-tested on sample descending CGM sequence ending at 48 mg/dL.

## Next
Integrate real Nightscout/LibreLinkUp sample stream; add multi-day residual window.
