#!/usr/bin/env python3
"""Phenotype-routed lifestyle nudge with a Generator–Verifier–Updater loop.

Prototypes the underexploited insight in Salunkhe, Sinha, Ahlqvist et al.,
npj Digital Medicine 2023: digital lifestyle treatment improved HbA1c, but the
response was larger in high-BMI / insulin-resistant participants and in
non-carriers of the FTO risk allele. The agent does not invent a new model;
it assigns a dose, checks it against that response pattern, and revises.

Educational prototype only. Not a medical device and not clinical advice.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


HIGH_BMI = 30.0
HIGH_IR = 2.5  # HOMA-IR proxy; paper used insulin resistance, not this cutoff
MIN_ACTIVITY_RESPONDER = 40
MIN_RESTRAINT_RESPONDER = 7
MAX_DROP_FTO_RISK = 4.0  # mmol/mol; non-risk carriers responded more
MIN_DROP_RESPONDER = 5.0


@dataclass
class Phenotype:
    participant_id: str
    bmi: float
    homa_ir: float
    fto_risk_allele: bool
    baseline_hba1c_mmol: float

    def stratum(self) -> str:
        bmi_band = "high_bmi" if self.bmi >= HIGH_BMI else "lower_bmi"
        ir_band = "high_ir" if self.homa_ir >= HIGH_IR else "lower_ir"
        gene = "fto_risk" if self.fto_risk_allele else "fto_nonrisk"
        return f"{bmi_band}+{ir_band}+{gene}"


@dataclass
class Nudge:
    participant_id: str
    stratum: str
    activity_min_per_day: int
    eating_restraint_score: int  # 0-10 cognitive restraint
    expected_hba1c_drop_mmol: float
    message: str
    medication_change: str = "none"
    revision_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Critique:
    passed: bool
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def generate(pheno: Phenotype, critique: Critique | None = None) -> Nudge:
    """Generator. First pass is a generic nudge; later passes apply critique."""
    notes: list[str] = []
    activity = 20
    restraint = 4
    drop = 4.0
    if critique is None:
        notes.append("pass-1 generic dose, ignoring phenotype")
    else:
        notes.append("revised from verifier critique")
        text = " ".join(critique.reasons).lower()
        responder = pheno.bmi >= HIGH_BMI and pheno.homa_ir >= HIGH_IR
        if "activity" in text or responder:
            activity = MIN_ACTIVITY_RESPONDER if responder else 25
            notes.append(f"activity set to {activity} for stratum")
        if "restraint" in text or responder:
            restraint = MIN_RESTRAINT_RESPONDER if responder else 5
            notes.append(f"restraint set to {restraint}")
        if "fto" in text or "drop" in text or "expected" in text:
            if pheno.fto_risk_allele:
                drop = min(MAX_DROP_FTO_RISK, 3.5)
                notes.append("capped expected drop for FTO risk allele")
            elif responder:
                drop = MIN_DROP_RESPONDER
                notes.append("raised expected drop for high-BMI/IR non-risk")
            else:
                drop = 3.0
                notes.append("modest expected drop for lower-response stratum")
        if responder and not pheno.fto_risk_allele:
            activity = max(activity, MIN_ACTIVITY_RESPONDER)
            restraint = max(restraint, MIN_RESTRAINT_RESPONDER)
            drop = max(drop, MIN_DROP_RESPONDER)
        elif responder and pheno.fto_risk_allele:
            activity = max(activity, MIN_ACTIVITY_RESPONDER)
            restraint = max(restraint, MIN_RESTRAINT_RESPONDER)
            drop = min(drop, MAX_DROP_FTO_RISK)

    stratum = pheno.stratum()
    message = (
        f"{stratum}: {activity} min brisk walking/day and cognitive "
        f"eating-restraint score {restraint}/10. Expected HbA1c change "
        f"-{drop:.1f} mmol/mol over follow-up. No medication change."
    )
    return Nudge(
        participant_id=pheno.participant_id,
        stratum=stratum,
        activity_min_per_day=activity,
        eating_restraint_score=restraint,
        expected_hba1c_drop_mmol=drop,
        message=message,
        revision_notes=notes,
    )


def verify(pheno: Phenotype, nudge: Nudge) -> Critique:
    """Falsifiable checks derived from the 2023 response pattern, not vibes."""
    reasons: list[str] = []
    responder = pheno.bmi >= HIGH_BMI and pheno.homa_ir >= HIGH_IR
    if nudge.medication_change != "none":
        reasons.append("medication_change must stay 'none' in this prototype")
    if nudge.stratum != pheno.stratum():
        reasons.append("stratum label does not match phenotype")
    if responder and nudge.activity_min_per_day < MIN_ACTIVITY_RESPONDER:
        reasons.append(
            f"activity {nudge.activity_min_per_day} < {MIN_ACTIVITY_RESPONDER} "
            "required for high-BMI + high-IR responders"
        )
    if responder and nudge.eating_restraint_score < MIN_RESTRAINT_RESPONDER:
        reasons.append(
            f"restraint {nudge.eating_restraint_score} < {MIN_RESTRAINT_RESPONDER} "
            "required for high-BMI + high-IR responders"
        )
    if pheno.fto_risk_allele and nudge.expected_hba1c_drop_mmol > MAX_DROP_FTO_RISK:
        reasons.append(
            f"expected drop {nudge.expected_hba1c_drop_mmol} exceeds "
            f"{MAX_DROP_FTO_RISK} cap for FTO risk allele"
        )
    if (
        responder
        and not pheno.fto_risk_allele
        and nudge.expected_hba1c_drop_mmol < MIN_DROP_RESPONDER
    ):
        reasons.append(
            f"expected drop {nudge.expected_hba1c_drop_mmol} < {MIN_DROP_RESPONDER} "
            "for high-BMI/IR non-risk carriers"
        )
    if not (0 <= nudge.eating_restraint_score <= 10):
        reasons.append("restraint score out of 0-10 range")
    return Critique(passed=len(reasons) == 0, reasons=reasons or ["all criteria met"])


def run_loop(pheno: Phenotype, passes: int = 3) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []
    critique: Critique | None = None
    nudge: Nudge | None = None
    for i in range(1, passes + 1):
        nudge = generate(pheno, critique)
        critique = verify(pheno, nudge)
        log.append(
            {
                "pass": i,
                "nudge": nudge.to_dict(),
                "verifier": critique.to_dict(),
            }
        )
        if critique.passed:
            break
    return log


def _plain(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_plain(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def main() -> None:
    sample = Phenotype(
        participant_id="P-310",
        bmi=33.4,
        homa_ir=3.8,
        fto_risk_allele=True,
        baseline_hba1c_mmol=62.0,
    )
    log = run_loop(sample, passes=3)
    print(json.dumps(_plain({
        "sample": {
            "participant_id": sample.participant_id,
            "bmi": sample.bmi,
            "homa_ir": sample.homa_ir,
            "fto_risk_allele": sample.fto_risk_allele,
            "baseline_hba1c_mmol": sample.baseline_hba1c_mmol,
            "stratum": sample.stratum(),
        },
        "passes": log,
    }), indent=2))


if __name__ == "__main__":
    main()
