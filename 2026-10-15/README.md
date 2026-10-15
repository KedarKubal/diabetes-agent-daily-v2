# 2026-10-15: Smartphone PPG Digital Biomarker GVU for Diabetes Detection

Minimal self-improving Generator-Verifier-Updater prototype of the underexploited insight in Tison et al. (Nature Medicine): deep neural net on ubiquitous smartphone-camera PPG as a noninvasive digital biomarker for prevalent diabetes.

**Verifier success criterion (explicit):** For high-risk sample, risk_score > 0.7, label matches expected, and features include long-range context (10+ min PPG) or demographics.

Smoke-tested on sample P-1510: pass 1 (0.65, missing long-range) failed; pass 2 (0.80 + long_range_context_10min) passed.

Base inspiration: simple multi-agent healthcare patterns (e.g., LangGraph/CrewAI style loops).
