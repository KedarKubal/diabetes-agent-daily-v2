#!/usr/bin/env python3
"""GVU prototype: monthly-calibrated PPG glucose + implicit HbA1c.

Opportunity: Chu et al. (2025) showed a single monthly pretest plus an
inferred HbA1c feature keeps wearable PPG estimates clinically safe
across medication cohorts. This script is a 2-hour slice of that idea:
Generator drafts a glucose + implicit A1c from mock dual-channel PPG,
Verifier checks explicit ISO-style / cohort bounds, Updater revises
channel weights and the A1c proxy for 3 passes.

Not medical advice. Synthetic data only.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal


Cohort = Literal["no_add", "oral_add", "oral_plus"]

# Clinical-style MARD ceilings inspired by Chu et al. cohort split
# (not a reproduction of their model).
MARD_CEILING = {"no_add": 10.0, "oral_add": 13.0, "oral_plus": 17.0}
A1C_RANGE = (4.5, 14.0)


@dataclass
class PpgSample:
    patient_id: str
    cohort: Cohort
    monthly_pretest_mgdl: float
    days_since_pretest: int
    red_ppg: float  # 660 nm intensity (normalized)
    ir_ppg: float  # 880 nm intensity (normalized)
    skin_temp_c: float
    true_glucose_mgdl: float  # held-out for smoke-test logging only


@dataclass
class Draft:
    predicted_mgdl: float
    implicit_a1c: float
    red_weight: float
    ir_weight: float
    notes: str
    pass_index: int


@dataclass
class Critique:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    mard_vs_pretest: float = 0.0


def implicit_a1c_from_pretest(pretest_mgdl: float, days: int) -> float:
    """Crude proxy: mean glucose -> eA1c, drift slightly with days."""
    eag = pretest_mgdl * (1.0 + 0.002 * days)
    a1c = (eag + 46.7) / 28.7
    return round(max(A1C_RANGE[0], min(A1C_RANGE[1], a1c)), 2)


def generate(sample: PpgSample, critique: Critique | None, prev: Draft | None) -> Draft:
    # Pass 1 is deliberately IR-underweighted so the verifier has work.
    red_w = prev.red_weight if prev else 0.78
    ir_w = prev.ir_weight if prev else 0.22
    a1c = prev.implicit_a1c if prev else implicit_a1c_from_pretest(
        sample.monthly_pretest_mgdl, sample.days_since_pretest
    )

    if critique and not critique.passed:
        # Updater rule: lean harder on IR (>1000 nm analogue) and
        # pull prediction toward monthly pretest as calibration anchor.
        ir_w = min(0.85, ir_w + 0.12)
        red_w = 1.0 - ir_w
        if critique.mard_vs_pretest > MARD_CEILING[sample.cohort]:
            a1c = round((a1c + implicit_a1c_from_pretest(sample.monthly_pretest_mgdl, 0)) / 2, 2)

    # Dual-channel blend + A1c-conditioned offset (the paper's seed insight)
    optical = 70.0 + 180.0 * (ir_w * sample.ir_ppg + red_w * sample.red_ppg)
    a1c_offset = (a1c - 6.5) * 12.0
    temp_offset = (sample.skin_temp_c - 33.0) * 1.5
    # Early passes trust optics more; later passes (after critique) mix in pretest.
    pretest_mix = 0.20 if (prev is None) else 0.55
    calib = pretest_mix * sample.monthly_pretest_mgdl + (1.0 - pretest_mix) * optical
    pred = calib + a1c_offset + temp_offset
    pred = max(40.0, min(400.0, pred))

    notes = (
        f"cohort={sample.cohort} red_w={red_w:.2f} ir_w={ir_w:.2f} "
        f"optical={optical:.1f} a1c={a1c}"
    )
    return Draft(
        predicted_mgdl=round(pred, 1),
        implicit_a1c=a1c,
        red_weight=round(red_w, 3),
        ir_weight=round(ir_w, 3),
        notes=notes,
        pass_index=(prev.pass_index + 1) if prev else 1,
    )


def verify(sample: PpgSample, draft: Draft) -> Critique:
    reasons: list[str] = []
    rel = abs(draft.predicted_mgdl - sample.monthly_pretest_mgdl) / sample.monthly_pretest_mgdl
    mard = rel * 100.0
    ceiling = MARD_CEILING[sample.cohort]

    if mard > ceiling:
        reasons.append(
            f"FAIL MARD-vs-monthly-pretest {mard:.1f}% > {ceiling}% for cohort {sample.cohort}"
        )
    else:
        reasons.append(f"OK MARD-vs-pretest {mard:.1f}% <= {ceiling}%")

    if not (A1C_RANGE[0] <= draft.implicit_a1c <= A1C_RANGE[1]):
        reasons.append(f"FAIL implicit A1c {draft.implicit_a1c} outside {A1C_RANGE}")
    else:
        reasons.append(f"OK implicit A1c {draft.implicit_a1c}")

    # Safety: do not emit a reading that would land in Clarke C+ if compared to pretest
    abs_err = abs(draft.predicted_mgdl - sample.monthly_pretest_mgdl)
    if abs_err > 80 and mard > 25:
        reasons.append("FAIL Clarke-C-like: large absolute and relative error vs pretest")

    passed = all(r.startswith("OK") for r in reasons)
    return Critique(passed=passed, reasons=reasons, mard_vs_pretest=round(mard, 2))


def run_gvu(sample: PpgSample, max_passes: int = 3) -> list[dict]:
    log: list[dict] = []
    critique: Critique | None = None
    draft: Draft | None = None
    for _ in range(max_passes):
        draft = generate(sample, critique, draft)
        critique = verify(sample, draft)
        log.append(
            {
                "pass": draft.pass_index,
                "draft": asdict(draft),
                "critique": asdict(critique),
            }
        )
        if critique.passed:
            break
    return log


def smoke_test() -> None:
    sample = PpgSample(
        patient_id="P-088",
        cohort="oral_add",
        monthly_pretest_mgdl=142.0,
        days_since_pretest=18,
        red_ppg=0.18,
        ir_ppg=0.22,
        skin_temp_c=33.4,
        true_glucose_mgdl=151.0,
    )
    log = run_gvu(sample)
    out_dir = Path(__file__).resolve().parent
    out_path = out_dir / "smoke_test.json"
    payload = {
        "sample": asdict(sample),
        "passes": log,
        "held_out_true_mgdl": sample.true_glucose_mgdl,
        "final_passed": log[-1]["critique"]["passed"],
    }
    out_path.write_text(json.dumps(payload, indent=2))
    print("=== GVU smoke test P-088 ===")
    for step in log:
        d = step["draft"]
        c = step["critique"]
        print(
            f"pass {step['pass']}: pred={d['predicted_mgdl']} "
            f"a1c={d['implicit_a1c']} ir_w={d['ir_weight']} "
            f"passed={c['passed']} mard={c['mard_vs_pretest']}"
        )
        for r in c["reasons"]:
            print(f"  - {r}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    smoke_test()
