# 2026-10-09 breath-acetone LOD gate

Fork-style base: tiny GVU script (same pattern as prior days; closest public multi-agent generator is https://github.com/vasiliskou/crewai-system-generator).

Run: `python gvu_breath_gate.py`

Verifier: effective LOD <= 1.5 ppm, selectivity vs ethanol >= 3, drift <= 0.5%, no diagnosis label, screen only if corrected acetone >= 1.8 ppm and >= LOD.
