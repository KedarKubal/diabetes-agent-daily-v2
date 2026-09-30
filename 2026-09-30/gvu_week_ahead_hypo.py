#!/usr/bin/env python3
"""
Week-ahead hypoglycemia risk GVU loop (Generator–Verifier–Updater).

Insight prototyped: a week of CGM summary metrics (TBR, %CV, GMI)
already carries enough signal to draft next-week severe-hypo risk
and a concrete care nudge — then self-correct against explicit rules.

Not medical advice. Research prototype only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Explicit, falsifiable success criteria (Verifier).
# Calibrated loosely to TBR/%CV/GMI features used in CGM-ML hypo papers.
CRITERIA = {
    "tbr70_high": 4.0,  # % time < 70 mg/dL — ADA TBR target is <4%
    "cv_unstable": 36.0,  # %CV > 36 is high glycemic variability
    "gmi_low": 6.4,  # very low GMI + high TBR implies over-treatment
    "required_fields": ("risk_level", "risk_score", "rationale", "nudge"),
    "allowed_levels": ("low", "moderate", "high"),
}


@dataclass
class WeekCGM:
    patient_id: str
    tbr70_pct: float  # time below 70 mg/dL, %
    tbr54_pct: float  # time below 54 mg/dL, %
    cv_pct: float
    gmi: float
    nocturnal_tbr70_pct: float


@dataclass
class Draft:
    risk_level: str
    risk_score: float
    rationale: str
    nudge: str
    extras: dict[str, Any] = field(default_factory=dict)


def _heuristic_score(week: WeekCGM) -> float:
    """0–100 score from published-style CGM features."""
    score = 0.0
    score += min(week.tbr70_pct, 20.0) * 4.0
    score += min(week.tbr54_pct, 10.0) * 6.0
    if week.cv_pct > CRITERIA["cv_unstable"]:
        score += (week.cv_pct - CRITERIA["cv_unstable"]) * 1.2
    if week.gmi < CRITERIA["gmi_low"] and week.tbr70_pct > 2.0:
        score += 12.0
    score += min(week.nocturnal_tbr70_pct, 15.0) * 1.5
    return round(min(score, 100.0), 1)


def _level_from_score(score: float) -> str:
    if score >= 45:
        return "high"
    if score >= 22:
        return "moderate"
    return "low"


def generate(week: WeekCGM, critique: str | None = None, pass_idx: int = 1) -> Draft:
    """Generator: draft week-ahead hypo risk + care nudge."""
    score = _heuristic_score(week)
    level = _level_from_score(score)

    # First pass is intentionally a bit sloppy so the loop has work to do.
    if pass_idx == 1 and not critique:
        rationale = (
            f"{week.patient_id} looks a bit variable this week "
            f"(CV {week.cv_pct}%). Maybe watch nights."
        )
        nudge = "Keep an eye on sugars and maybe eat a snack."
        # Under-call risk so verifier can reject missing TBR citation.
        if level == "high":
            level = "moderate"
            score = max(score - 18, 20)
        return Draft(level, score, rationale, nudge, {"pass": 1, "sloppy": True})

    reasons = []
    if week.tbr70_pct >= CRITERIA["tbr70_high"]:
        reasons.append(f"TBR<70 is {week.tbr70_pct}% (target <{CRITERIA['tbr70_high']}%)")
    else:
        reasons.append(f"TBR<70 is {week.tbr70_pct}% (within ADA <4% target)")
    if week.tbr54_pct > 0.5:
        reasons.append(f"TBR<54 is {week.tbr54_pct}% (clinically significant hypo time)")
    if week.cv_pct > CRITERIA["cv_unstable"]:
        reasons.append(f"%CV {week.cv_pct} exceeds 36% instability threshold")
    if week.nocturnal_tbr70_pct >= 3.0:
        reasons.append(f"nocturnal TBR {week.nocturnal_tbr70_pct}% — overnight clustering")
    if week.gmi < CRITERIA["gmi_low"] and week.tbr70_pct > 2.0:
        reasons.append(f"GMI {week.gmi} with elevated TBR suggests possible overtreatment")

    rationale = (
        f"Week-ahead severe-hypo risk for {week.patient_id} is {level} "
        f"(score {score}/100). " + "; ".join(reasons) + "."
    )
    if critique:
        rationale += f" Revised after critique: {critique[:160]}"

    if level == "high":
        nudge = (
            "Before next week: review basal/overnight insulin with clinician; "
            "set CGM urgent-low soon at 70; take 15g slow carb if TBR clusters after 22:00; "
            "do not increase insulin without a plan."
        )
    elif level == "moderate":
        nudge = (
            "Log bedtime glucose 3 nights; if <110 mg/dL with active insulin, "
            "add 10–15g protein+carb snack and recheck at 03:00 once."
        )
    else:
        nudge = (
            "Maintain current meal timing; keep CGM alerts on; "
            "recompute risk after the next 7 days of wear."
        )

    return Draft(level, score, rationale, nudge, {"pass": pass_idx, "sloppy": False})


def verify(week: WeekCGM, draft: Draft) -> tuple[bool, list[str]]:
    """
    Verifier success criterion (all must hold):
      1. Draft has required fields and an allowed risk_level.
      2. risk_score is in [0, 100] and matches heuristic within 5 points
         after pass 1 (pass 1 may be sloppy and should fail).
      3. If TBR<70 >= 4% OR TBR<54 >= 1% OR (CV>36 and nocturnal TBR>=3),
         risk_level must be 'high' (not under-called).
      4. If TBR<70 < 2% AND CV <= 36 AND TBR<54 < 0.5, level must be 'low'.
      5. Rationale must mention TBR and %CV by name.
      6. High-risk nudge must mention clinician or insulin review,
         and must not tell the user to increase insulin.
    """
    fails: list[str] = []

    for key in CRITERIA["required_fields"]:
        if not getattr(draft, key, None):
            fails.append(f"missing field: {key}")

    if draft.risk_level not in CRITERIA["allowed_levels"]:
        fails.append(f"invalid risk_level {draft.risk_level!r}")

    if not (0 <= draft.risk_score <= 100):
        fails.append(f"score {draft.risk_score} out of [0,100]")

    expected = _heuristic_score(week)
    if abs(draft.risk_score - expected) > 5:
        fails.append(
            f"score {draft.risk_score} disagrees with feature heuristic {expected} by >5"
        )

    high_trigger = (
        week.tbr70_pct >= CRITERIA["tbr70_high"]
        or week.tbr54_pct >= 1.0
        or (week.cv_pct > CRITERIA["cv_unstable"] and week.nocturnal_tbr70_pct >= 3.0)
    )
    low_trigger = (
        week.tbr70_pct < 2.0
        and week.cv_pct <= CRITERIA["cv_unstable"]
        and week.tbr54_pct < 0.5
    )
    if high_trigger and draft.risk_level != "high":
        fails.append(
            f"under-called risk: features require high, got {draft.risk_level}"
        )
    if low_trigger and draft.risk_level != "low":
        fails.append(
            f"over-called risk: features require low, got {draft.risk_level}"
        )

    text = (draft.rationale + " " + draft.nudge).lower()
    if "tbr" not in text:
        fails.append("rationale/nudge never names TBR")
    if "cv" not in text:
        fails.append("rationale/nudge never names %CV")

    if draft.risk_level == "high":
        if "clinician" not in draft.nudge.lower() and "insulin" not in draft.nudge.lower():
            fails.append("high-risk nudge lacks clinician or insulin review")
        lowered = draft.nudge.lower()
        if "increase insulin" in lowered and "do not increase insulin" not in lowered and "don't increase insulin" not in lowered:
            fails.append("unsafe nudge: tells user to increase insulin")

    return (len(fails) == 0, fails)


def run_gvu(week: WeekCGM, max_passes: int = 3) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []
    critique: str | None = None
    draft: Draft | None = None

    for i in range(1, max_passes + 1):
        draft = generate(week, critique=critique, pass_idx=i)
        ok, fails = verify(week, draft)
        entry = {
            "pass": i,
            "risk_level": draft.risk_level,
            "risk_score": draft.risk_score,
            "rationale": draft.rationale,
            "nudge": draft.nudge,
            "passed": ok,
            "fails": fails,
        }
        log.append(entry)
        if ok:
            break
        critique = "; ".join(fails)
    return log


SAMPLE = WeekCGM(
    patient_id="P-204",
    tbr70_pct=6.8,
    tbr54_pct=1.4,
    cv_pct=41.2,
    gmi=6.3,
    nocturnal_tbr70_pct=5.1,
)


def main() -> None:
    print("=== Sample week CGM ===")
    print(SAMPLE)
    print("\n=== GVU passes ===")
    log = run_gvu(SAMPLE, max_passes=3)
    for row in log:
        print(f"\n--- pass {row['pass']} passed={row['passed']} ---")
        print(f"level={row['risk_level']} score={row['risk_score']}")
        print(f"rationale: {row['rationale']}")
        print(f"nudge: {row['nudge']}")
        if row["fails"]:
            print(f"verifier: {row['fails']}")
    first, last = log[0], log[-1]
    print("\n=== before/after ===")
    print(f"before: {first['risk_level']} / {first['risk_score']} / {first['nudge']}")
    print(f"after:  {last['risk_level']} / {last['risk_score']} / {last['nudge']}")


if __name__ == "__main__":
    main()
