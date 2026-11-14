#!/usr/bin/env python3
"""
Minimal GVU prototype: Multimodal Wearable Prediabetes Risk Screener
Based on insights from digital biomarkers papers (e.g., smartwatch HRV/activity/temp + context
for personalized glucose deviation prediction). Generator produces a risk score + nudge;
Verifier checks against explicit criterion; Updater revises.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
import json

@dataclass
class Candidate:
    risk_score: float  # 0.0-1.0
    risk_level: str
    nudge: str
    features_used: List[str]
    pass_num: int

class Generator:
    def __init__(self):
        self.history = []

    def generate(self, features: Dict[str, Any], critique: str = "") -> Candidate:
        # Simple heuristic based on multimodal features: HRV (lower = higher risk),
        # activity variance, skin temp deviation, sleep quality proxy
        hrv = features.get("hrv_rmssd", 40)
        activity_var = features.get("activity_variance", 0.3)
        temp_dev = features.get("temp_deviation", 0.2)
        sleep = features.get("sleep_score", 0.7)

        base_score = 0.3
        if hrv < 30:
            base_score += 0.25
        if activity_var > 0.5:
            base_score += 0.2
        if temp_dev > 0.5:
            base_score += 0.15
        if sleep < 0.5:
            base_score += 0.1

        # Incorporate critique if present
        if "missing circadian" in critique.lower() or "add time" in critique.lower():
            base_score = min(1.0, base_score + 0.1)
            features_used = ["hrv", "activity_var", "temp_dev", "sleep", "circadian_proxy"]
        else:
            features_used = ["hrv", "activity_var", "temp_dev", "sleep"]

        score = min(1.0, max(0.0, base_score))
        level = "high" if score > 0.65 else "moderate" if score > 0.4 else "low"
        if score > 0.65:
            nudge = "Recommend 10-min post-meal walk + HRV breathing exercise; consult clinician for lab confirmation."
        elif score > 0.4:
            nudge = "Increase daily activity consistency; track sleep."
        else:
            nudge = "Maintain current habits; routine screening."

        if "specific" in critique.lower() or "actionable" in critique.lower():
            nudge += " Specifically: target RMSSD >35 via evening breathing."

        cand = Candidate(score, level, nudge, features_used, len(self.history) + 1)
        self.history.append(cand)
        return cand

class Verifier:
    def verify(self, cand: Candidate, features: Dict[str, Any]) -> Dict[str, Any]:
        # Explicit success criterion: score in [0,1], if high-risk features present
        # (low HRV or high variance) then score >=0.6 and nudge is specific/actionable
        # (contains 'walk' or 'breathing' or 'clinician'), not generic.
        passed = True
        reasons = []

        if not (0 <= cand.risk_score <= 1):
            passed = False
            reasons.append("Score out of [0,1]")

        high_risk_indicators = features.get("hrv_rmssd", 40) < 35 or features.get("activity_variance", 0) > 0.4
        if high_risk_indicators:
            if cand.risk_score < 0.6:
                passed = False
                reasons.append("High-risk features but score <0.6")
            if not any(kw in cand.nudge.lower() for kw in ["walk", "breathing", "clinician", "exercise"]):
                passed = False
                reasons.append("Nudge not specific/actionable for high-risk case")
        else:
            if cand.risk_score > 0.7:
                passed = False
                reasons.append("Low-risk features but inflated score")

        critique = "; ".join(reasons) if reasons else "OK"
        return {"pass": passed, "reason": critique, "score": cand.risk_score}

class Updater:
    def __init__(self, gen: Generator, ver: Verifier):
        self.gen = gen
        self.ver = ver
        self.log: List[Dict] = []

    def run_loop(self, features: Dict[str, Any], max_passes: int = 3) -> List[Dict]:
        critique = ""
        results = []
        for i in range(max_passes):
            cand = self.gen.generate(features, critique)
            ver_result = self.ver.verify(cand, features)
            entry = {
                "pass": i + 1,
                "candidate": {
                    "risk_score": round(cand.risk_score, 3),
                    "risk_level": cand.risk_level,
                    "nudge": cand.nudge,
                    "features_used": cand.features_used
                },
                "verifier": ver_result
            }
            results.append(entry)
            self.log.append(entry)
            if ver_result["pass"]:
                break
            critique = ver_result["reason"]
        return results

def smoke_test():
    features = {
        "hrv_rmssd": 25,  # low
        "activity_variance": 0.6,
        "temp_deviation": 0.4,
        "sleep_score": 0.45
    }
    gen = Generator()
    ver = Verifier()
    updater = Updater(gen, ver)
    results = updater.run_loop(features)
    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    smoke_test()
