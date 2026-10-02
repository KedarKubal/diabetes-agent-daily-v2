# 2026-10-03 — Next-day SMBG + BP hypoglycemia flag

Opportunity: Alexiadis et al., IEEE Access 2024, used 10-day SMBG and blood-pressure sequences from a self-management app (669 people, LOSO random forest). The unused product slice is a next-day flag for non-CGM type 2 users that must cite the driving feature (recent lows or SBP drop) and a carb/check plan.

Base to fork: https://github.com/aakriti1318/multi-agent-generator

Run: `python gvu_nextday_smbg_bp.py`

Smoke sample P-441: pass 1 label low/22 failed verifier; pass 2 label high/87 with SBP-drop feature and 15 g carb plan passed.

Not a medical device.
