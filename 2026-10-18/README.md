# Day 2026-10-18: Phenotype-Routed Lifestyle Dose GVU

Minimal self-improving multi-agent prototype of digital therapeutics opportunity for delaying diabetes onset via personalized lifestyle interventions routed by BMI, insulin resistance, and FTO genotype.

- Generator: proposes activity minutes + diet restraint score based on phenotype
- Verifier: checks predicted HbA1c drop >=0.3, activity +>=15 min, restraint +>=2
- Updater: feeds critique back, loops up to 3 times

Run: `python gvu_phenotype_lifestyle.py`
