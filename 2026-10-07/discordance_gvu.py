"""Day 2026-10-07 — CGM vs awareness-questionnaire discordance flag.

Prototype of the underexploited insight in Fisher et al., Diabetes 2025;74(Suppl 1):366-P:
CGM metrics discriminate severe-hypoglycemia history better than Gold/Clarke
awareness questionnaires. The product seed is not another hypo predictor; it is
a clinic flag when self-report says awareness is intact but CGM features do not.

GVU loop (CS329A): Generator -> Verifier -> Updater, 3 passes max.
No network, no model weights. Deterministic rules so the loop is falsifiable.
"""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any


# Explicit success criterion (falsifiable).
# A candidate passes only if ALL of the following hold:
# 1. awareness_label == "intact" (Gold score <= 2 mapped to intact).
# 2. At least two CGM risk features fire:
#    tbr_below_54_pct >= 1.0 OR cv_pct >= 36 OR nocturnal_low_count >= 2.
# 3. risk_band == "high_discordance".
# 4. clinician_action names one of: alarm_threshold, education_visit, caregiver_check.
PASS_ACTIONS = {"alarm_threshold", "education_visit", "caregiver_check"}


@dataclass
class Sample:
    patient_id: str
    gold_score: int  # 1-2 intact, >=3 impaired (Gold method)
    tbr_below_54_pct: float
    cv_pct: float
    nocturnal_low_count: int
    tir_pct: float


SAMPLE = Sample(
    patient_id="P-807",
    gold_score=2,
    tbr_below_54_pct=2.4,
    cv_pct=41.0,
    nocturnal_low_count=5,
    tir_pct=61.0,
)


def _features_fired(sample: Sample) -> list[str]:
    fired = []
    if sample.tbr_below_54_pct >= 1.0:
        fired.append("tbr_below_54")
    if sample.cv_pct >= 36:
        fired.append("cv")
    if sample.nocturnal_low_count >= 2:
        fired.append("nocturnal_low")
    return fired


def generate(sample: Sample, critique: str | None = None) -> dict[str, Any]:
    """Generator. Pass 1 emits the naive questionnaire-led draft (expected fail)."""
    fired = _features_fired(sample)
    intact = sample.gold_score <= 2
    if critique is None:
        return {
            "patient_id": sample.patient_id,
            "awareness_label": "intact" if intact else "impaired",
            "features_used": ["gold_score"],
            "risk_band": "low" if intact else "impaired_awareness",
            "clinician_action": "routine_followup",
            "rationale": "Gold score <= 2; no extra review scheduled.",
        }
    action = "education_visit"
    if sample.nocturnal_low_count >= 2:
        action = "alarm_threshold"
    if sample.tbr_below_54_pct >= 2.0 and sample.nocturnal_low_count >= 4:
        action = "caregiver_check"
    return {
        "patient_id": sample.patient_id,
        "awareness_label": "intact" if intact else "impaired",
        "features_used": ["gold_score", *fired],
        "risk_band": "high_discordance" if intact and len(fired) >= 2 else "aligned",
        "clinician_action": action,
        "rationale": (
            f"Gold={sample.gold_score} (intact) but CGM features {fired} disagree; "
            f"action={action}. Critique applied: {critique}"
        ),
    }


def verify(candidate: dict[str, Any], sample: Sample) -> dict[str, Any]:
    """Verifier. Returns pass/fail plus an explicit reason."""
    reasons: list[str] = []
    fired = _features_fired(sample)
    if candidate.get("awareness_label") != "intact":
        reasons.append("awareness_label must be intact for this discordance case")
    if len(fired) < 2:
        reasons.append("sample does not meet two-feature CGM risk bar")
    used = set(candidate.get("features_used") or [])
    if len(used.intersection(fired)) < 2:
        reasons.append(
            f"features_used must include >=2 of {fired}; got {sorted(used)}"
        )
    if candidate.get("risk_band") != "high_discordance":
        reasons.append("risk_band must be high_discordance, not questionnaire-led low")
    if candidate.get("clinician_action") not in PASS_ACTIONS:
        reasons.append(
            "clinician_action must be alarm_threshold, education_visit, or caregiver_check"
        )
    ok = not reasons
    return {
        "pass": ok,
        "reasons": reasons or ["all criteria met"],
        "criterion": (
            "intact Gold AND >=2 CGM risk features cited AND "
            "risk_band=high_discordance AND concrete clinician_action"
        ),
    }


def run_gvu(sample: Sample, max_passes: int = 3) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []
    critique: str | None = None
    for i in range(1, max_passes + 1):
        candidate = generate(sample, critique)
        verdict = verify(candidate, sample)
        log.append({"pass": i, "candidate": candidate, "verdict": verdict})
        if verdict["pass"]:
            break
        critique = "; ".join(verdict["reasons"])
    return log


def main() -> None:
    log = run_gvu(SAMPLE)
    summary = {
        "sample": asdict(SAMPLE),
        "passes": log,
        "before": log[0]["candidate"],
        "after": log[-1]["candidate"],
        "improved": log[0]["verdict"]["pass"] is False and log[-1]["verdict"]["pass"] is True,
    }
    print(json.dumps(summary, indent=2))
    out = Path(__file__).with_name("smoke_test.json")
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
