#!/usr/bin/env python3
"""
Minimal GVU (Generator-Verifier-Updater) prototype for personalized hypoglycemia risk flag + actionable nudge.
Based on the opportunity from multimodal agentic glucose control papers (e.g., GlucoAgent / DiabAgent style).
Self-improving loop: Generator proposes risk + nudge; Verifier checks explicit criterion; Updater revises.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
import json

@dataclass
class Candidate:
    risk_level: str
    risk_score: float
    nudge: str
    features_used: List[str]
    pass_num: int = 0

class Generator:
    def __init__(self):
        self.history = []

    def generate(self, sample: Dict[str, Any], critique: str = "") -> Candidate:
        # Simple rule-based "generator" that improves with critique
        tbr = sample.get("tbr_pct", 0.0)
        slope = sample.get("glucose_slope_mgdl_per_min", 0.0)
        nocturnal = sample.get("is_nocturnal", False)
        recent_carbs = sample.get("recent_carbs_g", 0)

        score = min(100.0, max(0.0, 40 + tbr * 8 - slope * 15 + (10 if nocturnal else 0) - recent_carbs * 0.5))
        level = "high" if score >= 70 else "moderate" if score >= 45 else "low"

        if "specific carb" in critique.lower() or "15g" in critique.lower():
            nudge = "High nocturnal hypo risk: consume 15g fast-acting carbs now and recheck in 15 min. Avoid exercise until stable."
            features = ["tbr", "slope", "nocturnal", "specific_carb_correction"]
        elif "generic" in critique.lower():
            nudge = "Monitor glucose closely; consider a snack if trending down."
            features = ["tbr", "slope"]
        else:
            # Initial
            if level == "high" and nocturnal:
                nudge = "Elevated risk: check for symptoms and consider carbs."
                features = ["tbr", "slope", "nocturnal"]
            else:
                nudge = "Standard monitoring recommended."
                features = ["tbr"]

        cand = Candidate(level, round(score, 1), nudge, features)
        self.history.append(cand)
        return cand

class Verifier:
    SUCCESS_CRITERION = (
        "For high nocturnal risk (TBR > 4% AND negative slope AND nocturnal=True): "
        "must have risk_score >= 70, risk_level='high', and nudge must contain explicit '15g' fast-acting carb correction."
    )

    def verify(self, candidate: Candidate, sample: Dict[str, Any]) -> Dict[str, Any]:
        tbr = sample.get("tbr_pct", 0)
        slope = sample.get("glucose_slope_mgdl_per_min", 0)
        nocturnal = sample.get("is_nocturnal", False)
        is_high_nocturnal = tbr > 4.0 and slope < 0 and nocturnal

        reasons = []
        passed = True

        if is_high_nocturnal:
            if candidate.risk_score < 70:
                passed = False
                reasons.append(f"Score {candidate.risk_score} < 70")
            if candidate.risk_level != "high":
                passed = False
                reasons.append(f"Level '{candidate.risk_level}' != 'high'")
            if "15g" not in candidate.nudge.lower() and "15 g" not in candidate.nudge.lower():
                passed = False
                reasons.append("Nudge missing explicit 15g carb correction")
        else:
            # For non-high cases, just ensure not over-alerting
            if candidate.risk_level == "high" and candidate.risk_score < 60:
                passed = False
                reasons.append("Over-alert without sufficient score")

        critique = "; ".join(reasons) if reasons else "Meets criterion"
        return {
            "pass": passed,
            "critique": critique,
            "criterion": self.SUCCESS_CRITERION
        }

class Updater:
    def __init__(self, generator: Generator, verifier: Verifier):
        self.generator = generator
        self.verifier = verifier
        self.logs: List[Dict] = []

    def run_loop(self, sample: Dict[str, Any], max_passes: int = 3) -> List[Dict]:
        critique = ""
        results = []
        for i in range(1, max_passes + 1):
            cand = self.generator.generate(sample, critique)
            cand.pass_num = i
            ver = self.verifier.verify(cand, sample)
            entry = {
                "pass": i,
                "candidate": {
                    "risk_level": cand.risk_level,
                    "risk_score": cand.risk_score,
                    "nudge": cand.nudge,
                    "features_used": cand.features_used
                },
                "verification": ver
            }
            results.append(entry)
            self.logs.append(entry)
            if ver["pass"]:
                break
            critique = ver["critique"]
        return results

def smoke_test():
    sample = {
        "patient_id": "P-1113",
        "tbr_pct": 5.8,
        "glucose_slope_mgdl_per_min": -1.2,
        "is_nocturnal": True,
        "recent_carbs_g": 5,
        "current_glucose": 68
    }
    print("=== Smoke Test Sample ===")
    print(json.dumps(sample, indent=2))

    gen = Generator()
    ver = Verifier()
    updater = Updater(gen, ver)

    results = updater.run_loop(sample, max_passes=3)

    print("\n=== GVU Loop Results ===")
    for r in results:
        print(f"Pass {r['pass']}: {r['candidate']['risk_level']} / {r['candidate']['risk_score']}")
        print(f"  Nudge: {r['candidate']['nudge']}")
        print(f"  Verifier: {'PASS' if r['verification']['pass'] else 'FAIL'} - {r['verification']['critique']}")

    # Before/after summary
    if len(results) >= 2:
        print("\n=== Before/After ===")
        print("Before (pass 1):", results[0]["candidate"])
        print("After (final):", results[-1]["candidate"])

    return results

if __name__ == "__main__":
    smoke_test()
