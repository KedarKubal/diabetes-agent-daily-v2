# 2026-11-09: Personalized Digital Therapeutic Lifestyle Nudge GVU

**Opportunity**: Prevention/Digital Therapeutics angle — self-improving agent that generates and verifies personalized lifestyle nudges (activity + cognitive restraint) until projected HbA1c improvement meets explicit threshold, inspired by subgroup-differentiated digital lifestyle effects.

**Base**: Minimal from-scratch prototype embodying the core insight of adaptive dosing of behavioral interventions.

**Verifier success criterion**: `projected_hba1c_drop >= 0.3` (falsifiable heuristic proxy for clinically meaningful improvement).

**Smoke test**: Sample P-1109 (high BMI, IR): pass1 low-intensity failed; pass2 intensified (45 min post-meal + sequencing) passed.

Run: `python gvu_lifestyle_nudge.py`
