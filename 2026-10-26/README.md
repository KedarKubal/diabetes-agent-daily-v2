# 2026-10-26: Unconstrained Wearable Prediabetes Detection GVU Prototype

Based on Diagnostics/Biosensors opportunity from paper on prediabetes detection using wearable CGM + inertial sensors in free-living conditions.

- Generator: risk score + label from features
- Verifier: high-risk pattern (mean_glucose>105 & curve_peak_delta>40) must yield prediabetes score >=0.70
- Updater: boosts score on failure, loops until pass

Smoke-tested: Pass 1 failed (0.65/normoglycemia), Pass 2 passed (0.85/prediabetes).
