#!/usr/bin/env python3
"""
Minimal GVU prototype for hypoglycemia risk flag from multi-modal wearable proxies.
Generator produces risk score + flag + nudge.
Verifier checks explicit criteria: score in [0,100], flag consistent with score, nudge specific if high.
Updater revises based on critique.
Smoke-tested on one sample.
"""

import json
from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class Candidate:
    risk_score: float
    flag: str  # "low", "moderate", "high"
    nudge: str
    features_used: list

def generator(input_data: Dict[str, Any], critique: str = "") -> Candidate:
    """Simple heuristic generator that improves with critique."""
    # Features: recent_slope, gsr_elevated, activity_recent, tbr_last_night
    slope = input_data.get("recent_slope", 0.0)  # mg/dL/min
    gsr = input_data.get("gsr_elevated", False)
    activity = input_data.get("activity_recent", False)
    tbr = input_data.get("tbr_last_night", 0.0)  # % time below range

    score = 20.0
    if slope < -1.5:
        score += 30
    if gsr:
        score += 25
    if activity:
        score += 15
    if tbr > 5:
        score += 20
    score = min(100, max(0, score))

    flag = "low" if score < 40 else "moderate" if score < 70 else "high"

    nudge = "Monitor closely."
    if score >= 70:
        nudge = "High risk: consume 15g fast carbs and recheck in 15 min."
    elif score >= 40:
        nudge = "Moderate: reduce activity or add snack if trending down."

    if critique:
        if "specific" in critique.lower() and score >= 70 and "15g" not in nudge:
            nudge = "High risk: consume 15g fast-acting carbs immediately and recheck glucose in 15 minutes."
        if "consistent" in critique.lower() and flag != ("high" if score >= 70 else "moderate" if score >= 40 else "low"):
            flag = "high" if score >= 70 else "moderate" if score >= 40 else "low"

    return Candidate(score, flag, nudge, ["slope", "gsr", "activity", "tbr"])

def verifier(candidate: Candidate, criterion: str = "score 0-100, flag matches score bands, high flag has specific carb nudge") -> Dict[str, Any]:
    """Explicit success criterion check."""
    passed = True
    reasons = []
    if not (0 <= candidate.risk_score <= 100):
        passed = False
        reasons.append("score out of range")
    expected_flag = "low" if candidate.risk_score < 40 else "moderate" if candidate.risk_score < 70 else "high"
    if candidate.flag != expected_flag:
        passed = False
        reasons.append("flag inconsistent with score")
    if candidate.flag == "high" and "15g" not in candidate.nudge.lower() and "carb" not in candidate.nudge.lower():
        passed = False
        reasons.append("high flag lacks specific carb nudge")
    return {"pass": passed, "reasons": reasons, "criterion": criterion}

def updater_loop(input_data: Dict[str, Any], max_passes: int = 3) -> list:
    log = []
    critique = ""
    for i in range(1, max_passes + 1):
        cand = generator(input_data, critique)
        v = verifier(cand)
        entry = {"pass": i, "candidate": asdict(cand), "verifier": v}
        log.append(entry)
        if v["pass"]:
            break
        critique = "; ".join(v["reasons"])
    return log

if __name__ == "__main__":
    sample = {
        "recent_slope": -2.1,
        "gsr_elevated": True,
        "activity_recent": True,
        "tbr_last_night": 8.5
    }
    result = updater_loop(sample)
    print(json.dumps(result, indent=2))
    with open("smoke_test_output.json", "w") as f:
        json.dump({"sample": sample, "log": result}, f, indent=2)
