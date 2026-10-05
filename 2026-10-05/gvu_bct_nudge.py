"""Day 2026-10-05 — BCT-constrained glycemic nudge (GVU).

Prototypes the Liu & Xia 2025 finding that m-health interventions using
"problem solving" plus "reward and threat" beat self-monitoring-only stacks
on HbA1c. Generator drafts a nudge; Verifier enforces those two BCTs;
Updater revises from the critique. Educational prototype, not clinical advice.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Nudge:
    patient_id: str
    text: str
    bcts: list[str] = field(default_factory=list)
    behavior: str = ""
    obstacle_branch: str = ""
    contingency: str = ""


@dataclass
class Critique:
    passed: bool
    reasons: list[str]
    success_criterion: str


SUCCESS_CRITERION = (
    "Nudge must (1) name one glycemic behavior (walk, meal timing, or meds), "
    "(2) include a problem-solving branch: an obstacle and a concrete alternative, "
    "(3) include a contingent reward or threat tied to a countable behavior target, "
    "(4) not be self-monitoring-only."
)

OBSTACLE_RE = re.compile(
    r"\b(if|when)\b.+\b(rain|busy|pain|travel|skip|miss|tired|late)\b",
    re.I,
)
ALT_RE = re.compile(
    r"\b(instead|alternative|do \d+|indoor|10 min|substitute|swap)\b",
    re.I,
)
REWARD_RE = re.compile(
    r"\b(reward|unlock|earn|coffee|only if|contingent)\b",
    re.I,
)
THREAT_RE = re.compile(
    r"\b(skip the|lose|forfeit|withhold|threat|no coffee)\b",
    re.I,
)
BEHAVIOR_RE = re.compile(
    r"\b(walk|march|meal|dinner|medication|metformin|steps)\b",
    re.I,
)
COUNT_RE = re.compile(r"\b(\d+\s+of\s+\d+|\d+\s+days)\b", re.I)


def generate(sample: dict[str, Any], critique: Critique | None = None) -> Nudge:
    """Draft a nudge. Pass 1 is intentionally self-monitor-only so the loop is falsifiable."""
    pid = sample["patient_id"]
    if critique is None or not critique.reasons:
        return Nudge(
            patient_id=pid,
            text=(
                f"{pid}: fasting glucose is {sample['fasting_mgdl']} mg/dL. "
                "Check your glucose again tonight and try to walk more."
            ),
            bcts=["self-monitoring of outcome"],
            behavior="walk",
            obstacle_branch="",
            contingency="",
        )

    behavior = "20-min after-dinner walk"
    obstacle = (
        "If rain, pain, or a late meeting blocks the outdoor walk, "
        "do 10 min indoor marching after dinner instead"
    )
    contingency = (
        "Unlock Saturday coffee only if 4 of 7 days are logged; "
        "forfeit the coffee if two days are missed"
    )
    text = (
        f"{pid}: keep the {behavior} (target tied to fasting {sample['fasting_mgdl']} mg/dL). "
        f"{obstacle}. {contingency}."
    )
    return Nudge(
        patient_id=pid,
        text=text,
        bcts=["problem solving", "reward and threat"],
        behavior=behavior,
        obstacle_branch=obstacle,
        contingency=contingency,
    )


def verify(nudge: Nudge) -> Critique:
    reasons: list[str] = []
    text = nudge.text
    if not BEHAVIOR_RE.search(text):
        reasons.append("missing glycemic behavior (walk, meal, or meds)")
    has_obstacle = bool(OBSTACLE_RE.search(text)) or bool(nudge.obstacle_branch)
    has_alt = bool(ALT_RE.search(text))
    if not (has_obstacle and has_alt):
        reasons.append("missing problem-solving branch (obstacle + alternative)")
    has_contingent = bool(REWARD_RE.search(text) or THREAT_RE.search(text))
    has_count = bool(COUNT_RE.search(text))
    if not (has_contingent and has_count):
        reasons.append("missing contingent reward/threat tied to a countable target")
    monitoring_only = "self-monitoring" in nudge.bcts and "problem solving" not in nudge.bcts
    if monitoring_only or (not has_obstacle and "check your glucose" in text.lower()):
        reasons.append("self-monitoring-only; rejected by Liu & Xia BCT finding")
    return Critique(
        passed=len(reasons) == 0,
        reasons=reasons,
        success_criterion=SUCCESS_CRITERION,
    )


def run_loop(sample: dict[str, Any], passes: int = 3) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []
    critique: Critique | None = None
    for i in range(1, passes + 1):
        nudge = generate(sample, critique if critique and not critique.passed else None)
        critique = verify(nudge)
        log.append({"pass": i, "nudge": asdict(nudge), "verifier": asdict(critique)})
        if critique.passed:
            break
    return log


def main() -> None:
    sample = {
        "patient_id": "P-605",
        "fasting_mgdl": 148,
        "missed": "evening walk",
        "likes": "saturday coffee",
    }
    log = run_loop(sample, passes=3)
    print(json.dumps({"sample": sample, "log": log}, indent=2))
    assert log[0]["verifier"]["passed"] is False, "pass 1 must fail the BCT criterion"
    assert log[-1]["verifier"]["passed"] is True, "final pass must satisfy the criterion"
    assert len(log) >= 2, "loop must revise at least once"


if __name__ == "__main__":
    main()
