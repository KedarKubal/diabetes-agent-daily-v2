"""Next-day hypoglycemia flag from a 10-day SMBG + blood-pressure sequence.

Prototypes the underexploited slice of Alexiadis et al., IEEE Access 2024:
joint glucose and blood-pressure history, not CGM-only, with a falsifiable
Generator-Verifier-Updater loop (CS329A GVU).

Not a medical device. Heuristic stand-in for the paper's random-forest signal.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DayRecord:
    day: int
    glucose_mg_dl: list[float]
    systolic_mmhg: float
    diastolic_mmhg: float


@dataclass
class Candidate:
    risk_label: str  # low | moderate | high
    score: float
    driving_feature: str
    action: str
    rationale: str


@dataclass
class Critique:
    passed: bool
    reasons: list[str] = field(default_factory=list)


def _lows(records: list[DayRecord], days: int, threshold: float = 70.0) -> int:
    window = records[-days:]
    return sum(1 for day in window for g in day.glucose_mg_dl if g < threshold)


def _mean_glucose(records: list[DayRecord]) -> float:
    values = [g for day in records for g in day.glucose_mg_dl]
    if not values:
        raise ValueError("glucose sequence is empty")
    return sum(values) / len(values)


def _bp_drop(records: list[DayRecord]) -> float:
    if len(records) < 4:
        return 0.0
    early = sum(d.systolic_mmhg for d in records[:3]) / 3
    late = sum(d.systolic_mmhg for d in records[-3:]) / 3
    return early - late


def generator(records: list[DayRecord], critique: Critique | None = None) -> Candidate:
    """Produce a next-day hypo flag. Incorporates verifier critique on later passes."""
    if not records:
        raise ValueError("records required")
    lows_3 = _lows(records, 3)
    lows_10 = _lows(records, 10)
    mean_g = _mean_glucose(records)
    drop = _bp_drop(records)

    # Pass 1 is intentionally under-sensitive (the failure the updater must fix).
    if critique is None:
        if lows_3 >= 3 and mean_g < 90:
            return Candidate(
                risk_label="moderate",
                score=48.0,
                driving_feature="recent_low_count",
                action="recheck glucose tomorrow morning",
                rationale="Saw some lows but did not escalate.",
            )
        return Candidate(
            risk_label="low",
            score=22.0,
            driving_feature="mean_glucose",
            action="continue usual logging",
            rationale="No escalation on first pass.",
        )

    text = " ".join(critique.reasons).lower()
    score = 20.0 + lows_10 * 12 + max(drop, 0) * 0.8 + (15 if mean_g < 110 else 0)
    if "escalate" in text or "high" in text or lows_3 >= 2:
        label = "high" if lows_3 >= 2 or (mean_g < 100 and drop >= 8) else "moderate"
        feature = "sbp_drop_plus_lows" if drop >= 8 else "recent_low_count"
        action = (
            "next-day hypo plan: check glucose before breakfast, 15 g carb if <80, "
            "hold extra activity, message caregiver if a second low occurs"
        )
        if label == "high":
            score = max(score, 70.0)
        return Candidate(label, round(score, 1), feature, action, "Revised from verifier critique.")
    return Candidate(
        "low",
        round(min(score, 35.0), 1),
        "stable_glucose_and_bp",
        "continue usual logging; no next-day hypo plan",
        "Stable window confirmed after critique.",
    )


def verifier(records: list[DayRecord], candidate: Candidate) -> Critique:
    """Falsifiable success criterion for the next-day flag.

    Pass iff all of:
    1. >=2 glucose values <70 mg/dL in the last 3 days => label high AND
       action names a carb/check plan AND driving_feature is set.
    2. Else if mean glucose <100 and systolic drop >=8 mmHg => label high or moderate
       AND driving_feature mentions bp or sbp.
    3. Else if every glucose in 90-160 and |systolic drop| <5 => label low.
    4. score in [0, 100] and label in {low, moderate, high}.
    """
    reasons: list[str] = []
    if candidate.risk_label not in {"low", "moderate", "high"}:
        reasons.append("label must be low, moderate, or high")
    if not 0 <= candidate.score <= 100:
        reasons.append("score out of range")
    lows_3 = _lows(records, 3)
    mean_g = _mean_glucose(records)
    drop = _bp_drop(records)
    all_stable = all(90 <= g <= 160 for day in records for g in day.glucose_mg_dl) and abs(drop) < 5

    if lows_3 >= 2:
        if candidate.risk_label != "high":
            reasons.append("escalate: >=2 lows in 3 days requires high")
        if "carb" not in candidate.action.lower() and "15 g" not in candidate.action.lower():
            reasons.append("action must include a carb/check plan")
        if not candidate.driving_feature:
            reasons.append("driving_feature required")
    elif mean_g < 100 and drop >= 8:
        if candidate.risk_label == "low":
            reasons.append("escalate: low mean glucose plus SBP drop cannot be low")
        if "bp" not in candidate.driving_feature.lower() and "sbp" not in candidate.driving_feature.lower():
            reasons.append("driving_feature must cite blood pressure")
    elif all_stable and candidate.risk_label != "low":
        reasons.append("stable glucose and BP must stay low")

    return Critique(passed=not reasons, reasons=reasons or ["meets success criterion"])


def updater(records: list[DayRecord], passes: int = 3) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []
    critique: Critique | None = None
    for i in range(1, passes + 1):
        candidate = generator(records, critique)
        critique = verifier(records, candidate)
        log.append(
            {
                "pass": i,
                "candidate": asdict(candidate),
                "verifier_passed": critique.passed,
                "reasons": critique.reasons,
            }
        )
        if critique.passed:
            break
    return log


SAMPLE = [
    DayRecord(1, [118, 142], 132, 82),
    DayRecord(2, [110, 136], 130, 80),
    DayRecord(3, [96, 128], 128, 80),
    DayRecord(4, [88, 120], 126, 78),
    DayRecord(5, [84, 102], 122, 76),
    DayRecord(6, [78, 96], 120, 76),
    DayRecord(7, [72, 90], 116, 74),
    DayRecord(8, [66, 94, 108], 112, 72),
    DayRecord(9, [62, 88], 110, 70),
    DayRecord(10, [68, 92], 108, 70),
]


def main() -> None:
    trail = updater(SAMPLE, passes=3)
    print(json.dumps(trail, indent=2))
    assert trail[0]["verifier_passed"] is False
    assert trail[-1]["verifier_passed"] is True
    assert trail[-1]["candidate"]["risk_label"] == "high"


if __name__ == "__main__":
    main()
