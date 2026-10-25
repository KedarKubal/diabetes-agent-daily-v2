#!/usr/bin/env python3
"""Minimal GVU prototype: Generator-Verifier-Updater for explainable CGM hypo risk score.
Based on Duckworth et al. 2024 insight: SHAP-style explanations for personalized risk."""

import json
from typing import Dict, Any

class Generator:
    def generate(self, sample: Dict[str, Any], critique: str = "") -> Dict[str, Any]:
        # Simple heuristic based on features: slope, TBR, mean glucose
        slope = sample.get("glucose_slope", 0)
        tbr = sample.get("time_below_range_24h", 0)
        mean_g = sample.get("mean_glucose_24h", 120)
        
        score = min(100, max(0, 50 + slope * 10 + tbr * 2 - (mean_g - 120) * 0.1))
        risk = "high" if score > 70 else "moderate" if score > 40 else "low"
        explanation = f"Risk driven by slope={slope:.1f} mg/dL/min, TBR={tbr:.1f}%, mean={mean_g:.0f}."
        nudge = "Consider 15g fast-acting carb if trending low." if risk == "high" else "Monitor trends closely."
        
        if "missing nocturnal" in critique.lower():
            explanation += " Nocturnal pattern considered."
            if tbr > 5:
                nudge = "Pre-bed 15g complex carb to prevent nocturnal hypo."
        
        return {
            "risk_score": round(score, 1),
            "risk_level": risk,
            "explanation": explanation,
            "nudge": nudge
        }

class Verifier:
    def verify(self, output: Dict[str, Any], sample: Dict[str, Any]) -> Dict[str, Any]:
        score = output.get("risk_score", 0)
        expl = output.get("explanation", "")
        success = 0 <= score <= 100 and "slope" in expl.lower() and "tbr" in expl.lower()
        reason = "Pass: score in range and explanation cites key features." if success else "Fail: score invalid or missing feature citations in explanation."
        if sample.get("time_below_range_24h", 0) > 10 and "nocturnal" not in expl.lower():
            success = False
            reason = "Fail: high TBR but missing nocturnal consideration in explanation."
        return {"pass": success, "reason": reason}

class Updater:
    def __init__(self):
        self.generator = Generator()
        self.verifier = Verifier()
    
    def run_loop(self, sample: Dict[str, Any], max_passes: int = 3) -> list:
        logs = []
        critique = ""
        for i in range(max_passes):
            output = self.generator.generate(sample, critique)
            ver = self.verifier.verify(output, sample)
            logs.append({"pass": i+1, "output": output, "verification": ver})
            if ver["pass"]:
                break
            critique = ver["reason"]
        return logs

if __name__ == "__main__":
    sample = {
        "glucose_slope": -1.5,
        "time_below_range_24h": 12.0,
        "mean_glucose_24h": 110
    }
    updater = Updater()
    results = updater.run_loop(sample)
    print(json.dumps(results, indent=2))
