# 2026-10-02 — Phenotype-routed lifestyle dose (GVU)

Educational prototype of the response-stratum insight in Salunkhe, Sinha et al.,
npj Digital Medicine 2023 (doi:10.1038/s41746-023-00946-0).

Not a medical device. Do not use for diagnosis or treatment.

## Run

```bash
python3 gvu_agent.py
```

Verifier criteria (falsifiable):

- High BMI (>=30) and high HOMA-IR proxy (>=2.5) must get activity >= 40 min/day and restraint >= 7.
- FTO risk-allele carriers must not be assigned an expected HbA1c drop above 4.0 mmol/mol.
- High-BMI/IR non-risk carriers must be assigned an expected drop of at least 5.0 mmol/mol.
- No medication change; stratum label must match the phenotype.
