"""Context-Horizon Hypoglycemia Gate (GVU).

Prototypes the underexploited insight in Quader et al. 2025 (J Diabetes Metab Disord):
CGM alerts stop at ~30 min; ML extends the horizon only when insulin, carbohydrate,
and activity context are inputs, and clinical utility depends on the patient's
daily hypoglycemia risk profile (false-positive budget).

Not a medical device. Synthetic sample only.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Sample:
    patient_id: str
    horizon_min: int
    glucose_mgdl: float
    slope_mgdl_per_min: float
    insulin_on_board_u: float | None
    carb_residual_g: float | None
    activity_met: float | None
    daily_hypo_rate: float  # events/day; sets the FP budget


@dataclass
class Flag:
    patient_id: str
    risk: str  # low | moderate | high
    score: float
    horizon_min: int
    features_used: list[str]
    action: str
    fp_budget: float
    rationale: str


def _missing(sample: Sample) -> list[str]:
    missing = []
    if sample.insulin_on_board_u is None:
        missing.append("insulin_on_board_u")
    if sample.carb_residual_g is None:
        missing.append("carb_residual_g")
    if sample.activity_met is None:
        missing.append("activity_met")
    return missing


def generate(sample: Sample, critique: str | None = None) -> Flag:
    """Generator. First pass ignores context (the common failure mode)."""
    use_context = critique is not None and "context" in critique.lower()
    missing = _missing(sample)
    features = ["glucose_mgdl", "slope_mgdl_per_min"]
    score = 0.35
    if sample.glucose_mgdl < 90:
        score += 0.25
    if sample.slope_mgdl_per_min < -0.8:
        score += 0.25

    action = "watch CGM"
    rationale = "Glucose and slope only; horizon alert without context."

    if use_context and not missing:
        features.extend(["insulin_on_board_u", "carb_residual_g", "activity_met"])
        score += min(0.25, sample.insulin_on_board_u * 0.08)
        score += 0.1 if sample.activity_met >= 3.0 else 0.0
        score -= min(0.3, sample.carb_residual_g * 0.01)
        score = max(0.0, min(1.0, score))
        if score >= 0.7:
            action = (
                f"Within {sample.horizon_min} min: take 15 g fast carb now; "
                f"IOB {sample.insulin_on_board_u:.1f} U still active; "
                f"pause activity (MET {sample.activity_met:.1f})."
            )
        elif score >= 0.45:
            action = "Recheck in 15 min; keep 15 g carb ready; do not add bolus."
        else:
            action = "No extra action; context offsets the slope."
        rationale = (
            f"Context-aware {sample.horizon_min} min flag. "
            f"IOB={sample.insulin_on_board_u}, carbs_left={sample.carb_residual_g}, "
            f"MET={sample.activity_met}. FP budget={sample.daily_hypo_rate:.2f}/day."
        )

    risk = "high" if score >= 0.7 else "moderate" if score >= 0.45 else "low"
    return Flag(
        patient_id=sample.patient_id,
        risk=risk,
        score=round(score, 3),
        horizon_min=sample.horizon_min,
        features_used=features,
        action=action,
        fp_budget=sample.daily_hypo_rate,
        rationale=rationale,
    )


def verify(sample: Sample, flag: Flag) -> dict[str, Any]:
    """Pass only if horizon is (30, 120], context features are present,
    score is in [0, 1], fp_budget matches daily hypo rate, and the labeled
    high-risk pattern includes a 15 g carb action.
    """
    reasons: list[str] = []
    required = {"insulin_on_board_u", "carb_residual_g", "activity_met"}
    if not (30 < flag.horizon_min <= 120):
        reasons.append("horizon must be beyond 30 min and at most 120 min")
    if not required.issubset(set(flag.features_used)):
        reasons.append("context features missing: need insulin, carb residual, activity")
    if flag.score < 0 or flag.score > 1:
        reasons.append("score out of [0, 1]")
    if abs(flag.fp_budget - sample.daily_hypo_rate) > 1e-6:
        reasons.append("fp_budget must equal patient daily hypo rate")
    expected_high = (
        sample.insulin_on_board_u is not None
        and sample.carb_residual_g is not None
        and sample.activity_met is not None
        and sample.glucose_mgdl < 80
        and sample.slope_mgdl_per_min < -1
        and sample.insulin_on_board_u >= 1.5
        and sample.carb_residual_g < 10
        and sample.activity_met >= 3
    )
    if expected_high:
        if flag.risk != "high":
            reasons.append("expected high risk given IOB, low carb residual, and activity")
        if "15 g" not in flag.action and "15g" not in flag.action:
            reasons.append("high-risk action must name a 15 g carb correction")
    passed = not reasons
    return {"pass": passed, "reasons": reasons or ["ok"]}


def update_loop(sample: Sample, passes: int = 3) -> list[dict[str, Any]]:
    critique: str | None = None
    log: list[dict[str, Any]] = []
    for i in range(1, passes + 1):
        flag = generate(sample, critique)
        verdict = verify(sample, flag)
        log.append({"pass": i, "flag": asdict(flag), "verdict": verdict})
        if verdict["pass"]:
            break
        critique = "context required; " + "; ".join(verdict["reasons"])
    return log


def main() -> None:
    sample = Sample(
        patient_id="P-718",
        horizon_min=60,
        glucose_mgdl=72,
        slope_mgdl_per_min=-1.4,
        insulin_on_board_u=2.2,
        carb_residual_g=4,
        activity_met=4.5,
        daily_hypo_rate=0.4,
    )
    log = update_loop(sample)
    print(json.dumps({"sample": asdict(sample), "log": log}, indent=2))


if __name__ == "__main__":
    main()
