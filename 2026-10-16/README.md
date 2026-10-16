# 2026-10-16: PPG Digital Biomarker GVU

Prototype of self-improving multi-agent for early diabetes detection via smartphone PPG.

## Opportunity
From Tison et al. Nature Medicine (A Digital Biomarker of Diabetes from Smartphone-Based Vascular Signals): underexploited insight is using existing phone cameras for scalable, non-invasive screening with deep temporal features.

## Run
```bash
python gvu_ppg_diabetes.py
```

## Success Criterion
Verifier requires risk_score in [0,1], long_range temporal feature, and score >=0.6.
