# 2026-10-04 — 14-day silent prediabetes screen

Fork-style base: [Glycemic Sentinel](https://github.com/maverickkamal/T1d-swarm) (multi-agent glycemic workflow). Today's slice does not depend on that stack.

Insight from arXiv:2410.02692: person-level prediabetes screen from OGTT-inspired curve features, not a glucose point estimate.

Run:

```bash
python3 gvu_prediabetes_screen.py
```

Sample P-514: pass 1 fails (normoglycemia + step_count + mg/dL estimate); pass 2 passes with the three breached curve drivers and a confirm-with-OGTT next step.
