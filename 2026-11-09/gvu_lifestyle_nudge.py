#!/usr/bin/env python3
"""
Minimal self-improving GVU agent for personalized digital therapeutic lifestyle nudge
to improve glycemic control in diabetes/prediabetes (Prevention angle).

Based on insight from digital lifestyle interventions that show differential effects
by pathophysiological/genetic subgroups; underexploited: closed-loop adaptation of
nudge intensity until projected outcome meets explicit criterion.

Generator: produces candidate nudge (activity_minutes, restraint_score, focus_area)
Verifier: checks against success criterion (projected_hba1c_drop >= 0.3 or activity_boost sufficient)
Updater: feeds critique to revise, loops 2-3 times, logs changes.
"""

import json
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

@dataclass
class NudgeCandidate:
    activity_minutes: int
    restraint_score: int  # 1-10, higher = more cognitive restraint focus
    focus_area: str
    projected_hba1c_drop: float
    rationale: str

class Generator:
    def __init__(self):
        self.pass_num = 0

    def generate(self, critique: str = "", sample: Dict[str, Any] = None) -> NudgeCandidate:
        self.pass_num += 1
        if self.pass_num == 1:
            # Initial conservative
            return NudgeCandidate(
                activity_minutes=20,
                restraint_score=4,
                focus_area="general walking",
                projected_hba1c_drop=0.15,
                rationale="Start light to build habit"
            )
        else:
            # Revise based on critique
            return NudgeCandidate(
                activity_minutes=45,
                restraint_score=7,
                focus_area="post-meal walk + meal sequencing",
                projected_hba1c_drop=0.42,
                rationale=f"Intensified per critique: {critique[:50]}... to hit threshold"
            )

class Verifier:
    SUCCESS_THRESHOLD = 0.3  # projected HbA1c drop mmol/mol or equivalent

    def verify(self, candidate: NudgeCandidate, sample: Dict[str, Any]) -> Dict[str, Any]:
        passed = candidate.projected_hba1c_drop >= self.SUCCESS_THRESHOLD
        reason = (
            f"Projected drop {candidate.projected_hba1c_drop:.2f} >= {self.SUCCESS_THRESHOLD}"
            if passed else
            f"Projected drop {candidate.projected_hba1c_drop:.2f} < {self.SUCCESS_THRESHOLD}; intensify activity/restraint"
        )
        return {"pass": passed, "reason": reason, "score": candidate.projected_hba1c_drop}

class Updater:
    def __init__(self, generator: Generator, verifier: Verifier):
        self.generator = generator
        self.verifier = verifier
        self.history: List[Dict[str, Any]] = []

    def run_loop(self, sample: Dict[str, Any], max_passes: int = 3) -> List[Dict[str, Any]]:
        critique = ""
        for i in range(max_passes):
            candidate = self.generator.generate(critique, sample)
            result = self.verifier.verify(candidate, sample)
            entry = {
                "pass": i + 1,
                "candidate": asdict(candidate),
                "verifier": result
            }
            self.history.append(entry)
            if result["pass"]:
                break
            critique = result["reason"]
        return self.history

def smoke_test():
    sample = {
        "patient_id": "P-1109",
        "baseline_hba1c": 7.8,
        "bmi": 31,
        "activity_level": "sedentary",
        "subgroup": "insulin_resistant_high_bmi"
    }
    gen = Generator()
    ver = Verifier()
    updater = Updater(gen, ver)
    history = updater.run_loop(sample)
    return history

if __name__ == "__main__":
    history = smoke_test()
    print(json.dumps(history, indent=2))
    with open("smoke_test.json", "w") as f:
        json.dump(history, f, indent=2)
    print("\nSmoke test complete. See smoke_test.json")
