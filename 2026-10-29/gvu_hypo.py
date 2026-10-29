#!/usr/bin/env python3
"""
Minimal GVU prototype for explainable CGM hypoglycemia risk flag + nudge.
Based on insight from Duckworth et al. 2024 / Cichosz et al. 2024: feature-engineered
CGM patterns (TBR, slope, CV) enable precise ahead-of-time hypo prediction;
the underexploited part is closing the loop with self-critique for actionable specificity.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
import json

@dataclass
class CGMFeatures:
    recent_tbr_pct: float  # time below range last 24h
    slope_mgdl_per_min: float  # recent glucose slope
    cv_pct: float  # coefficient of variation
    mean_glucose: float
    nocturnal_flag: bool = False

def generator(features: CGMFeatures, critique: str = "", pass_num: int = 1) -> Dict[str, Any]:
    """Generator: produce risk score, level, and nudge. Improves with critique."""
    score = 35.0
    reasons = []
    
    if features.recent_tbr_pct > 4.0:
        score += 20
        reasons.append("elevated_TBR")
    if features.slope_mgdl_per_min < -1.0:
        score += 15
        reasons.append("negative_slope")
    if features.cv_pct > 36:
        score += 10
        reasons.append("high_CV")
    if features.mean_glucose < 110:
        score += 8
        reasons.append("low_mean")
    if features.nocturnal_flag:
        score += 8
        reasons.append("nocturnal_risk")
    
    # Boost on critique / later passes
    if pass_num > 1 or "specific" in critique.lower() or "carb" in critique.lower():
        score += 25
        if "nocturnal" in critique.lower() and features.nocturnal_flag:
            reasons.append("nocturnal_specific")
    
    level = "high" if score >= 70 else "moderate" if score >= 50 else "low"
    
    # Initial generic nudge
    nudge = "Monitor glucose levels regularly."
    if level == "high" and (pass_num > 1 or "carb" in critique.lower()):
        nudge = "High hypo risk: take 15g fast-acting carbs now and recheck in 15 min. Consider reducing basal if pattern continues."
        if features.nocturnal_flag:
            nudge += " Bedtime snack with 15g carbs recommended."
    elif level == "moderate":
        nudge = "Moderate risk: check glucose soon and have carbs available."
    
    return {
        "risk_score": round(min(100, score), 1),
        "risk_level": level,
        "reasons": reasons,
        "nudge": nudge,
        "features_used": list(vars(features).keys())
    }

def verifier(output: Dict[str, Any], features: CGMFeatures) -> Dict[str, Any]:
    """Verifier: explicit success criterion.
    Pass if: (a) if TBR>4 or slope<-1 then level=='high' and score>=70,
    (b) for high, nudge contains '15g' or 'carb' and is specific (len>60),
    (c) reasons list non-empty when high.
    """
    issues = []
    expected_high = features.recent_tbr_pct > 4.0 or features.slope_mgdl_per_min < -1.0
    
    if expected_high:
        if output["risk_level"] != "high":
            issues.append("expected high risk level")
        if output["risk_score"] < 70:
            issues.append("score below 70 for high-risk features")
        if "carb" not in output["nudge"].lower() and "15g" not in output["nudge"].lower():
            issues.append("missing specific carb nudge")
        if len(output["nudge"]) < 60:
            issues.append("nudge not specific enough")
        if not output["reasons"]:
            issues.append("missing reasons")
    
    passed = len(issues) == 0
    critique = "PASS" if passed else "; ".join(issues) + ". Add specific 15g carb guidance, especially nocturnal if flagged."
    return {"pass": passed, "critique": critique, "issues": issues}

def updater_loop(features: CGMFeatures, max_passes: int = 3) -> List[Dict[str, Any]]:
    """Run GVU loop, logging each pass."""
    log = []
    critique = ""
    for i in range(1, max_passes + 1):
        gen_out = generator(features, critique, pass_num=i)
        ver = verifier(gen_out, features)
        entry = {
            "pass": i,
            "generator_output": gen_out,
            "verifier": ver
        }
        log.append(entry)
        if ver["pass"]:
            break
        critique = ver["critique"]
    return log

if __name__ == "__main__":
    # Smoke test sample: high-risk (elevated TBR, negative slope, nocturnal)
    sample = CGMFeatures(
        recent_tbr_pct=5.2,
        slope_mgdl_per_min=-1.8,
        cv_pct=42.0,
        mean_glucose=105,
        nocturnal_flag=True
    )
    result = updater_loop(sample)
    print(json.dumps(result, indent=2))
    with open("smoke_test_output.json", "w") as f:
        json.dump(result, f, indent=2)
