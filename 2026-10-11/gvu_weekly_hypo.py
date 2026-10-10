#!/usr/bin/env python3
"""
GVU Agent for Weekly Hypoglycemia Risk Flag + Personalized Nudge
Based on Cichosz et al. 2024 (XGBoost on CGM features: LBGI, GRADE, TBR, CV, etc.)

Generator: drafts risk score + nudge from sample weekly features
Verifier: checks if risk is correctly classified (high if LBGI>1.1 or TBR>4%) AND nudge addresses the top feature
Updater: revises based on critique, up to 3 passes
"""

import json
from datetime import datetime

# Sample patient data (inspired by paper features)
SAMPLE = {
    "patient_id": "P-1111",
    "week_features": {
        "lbgi": 1.35,          # Low Blood Glucose Index
        "grade": 2.8,          # GRADE score
        "tbr_pct": 5.2,        # Time Below Range %
        "cv": 38.5,            # Coefficient of Variation
        "mean_glucose": 142,
        "waveform_length": 120
    },
    "context": "T1D, uses CGM, history of nocturnal lows"
}

SUCCESS_CRITERIA = {
    "high_risk_threshold": {"lbgi": 1.1, "tbr_pct": 4.0},
    "nudge_must_address": ["lbgi", "tbr", "nocturnal", "correction"]
}

def generator(features, critique=None, pass_num=1):
    """Produces candidate: risk_level, score, nudge"""
    lbgi = features["lbgi"]
    tbr = features["tbr_pct"]
    cv = features["cv"]
    
    # Base risk calculation
    risk_score = (lbgi * 30) + (tbr * 5) + (cv * 0.3)
    risk_level = "high" if (lbgi > 1.1 or tbr > 4.0) else "moderate"
    
    if critique and "nudge too generic" in critique.lower():
        nudge = (
            f"High risk this week (score {risk_score:.1f}). "
            "Your LBGI is elevated — plan a 15g fast-acting carb correction "
            "before bed if CGM trend is downward after 10pm. "
            "Also reduce basal 10% on high-activity days."
        )
    elif critique and "score too low" in critique.lower():
        risk_score += 10
        risk_level = "high"
        nudge = f"Revised high risk ({risk_score:.1f}). Prioritize nocturnal monitoring."
    else:
        nudge = (
            f"{risk_level.capitalize()} weekly hypo risk (score {risk_score:.1f}). "
            "Review last week's patterns and stay consistent with meals."
        )
    
    return {
        "pass": pass_num,
        "risk_level": risk_level,
        "risk_score": round(risk_score, 1),
        "nudge": nudge,
        "top_feature": "lbgi" if lbgi > 1.1 else "tbr"
    }

def verifier(output, features):
    """Checks against explicit criteria. Returns pass/fail + reason"""
    reasons = []
    is_high = features["lbgi"] > 1.1 or features["tbr_pct"] > 4.0
    expected_level = "high" if is_high else "moderate"
    
    if output["risk_level"] != expected_level:
        reasons.append(f"risk_level mismatch: got {output['risk_level']}, expected {expected_level}")
    
    if is_high and output["risk_score"] < 40:
        reasons.append("score too low for high-risk features")
    
    nudge_lower = output["nudge"].lower()
    addresses = any(kw in nudge_lower for kw in ["carb", "correction", "nocturnal", "basal", "lbgi", "bed"])
    if not addresses:
        reasons.append("nudge too generic — does not address LBGI/TBR/nocturnal correction")
    
    passed = len(reasons) == 0
    return {
        "pass": passed,
        "reason": "; ".join(reasons) if reasons else "Meets criteria: correct level, score, and actionable nudge"
    }

def updater_loop(features, max_passes=3):
    """Run GVU loop, log each pass"""
    log = []
    critique = None
    for i in range(1, max_passes + 1):
        candidate = generator(features, critique, i)
        ver = verifier(candidate, features)
        entry = {
            "pass": i,
            "candidate": candidate,
            "verifier": ver,
            "timestamp": datetime.utcnow().isoformat()
        }
        log.append(entry)
        if ver["pass"]:
            break
        critique = ver["reason"]
    return log

if __name__ == "__main__":
    result = updater_loop(SAMPLE["week_features"])
    print(json.dumps(result, indent=2))
    
    # Smoke test summary
    final = result[-1]
    print(f"\n=== SMOKE TEST ===")
    print(f"Patient: {SAMPLE['patient_id']}")
    print(f"Passes: {len(result)}")
    print(f"Final risk: {final['candidate']['risk_level']} ({final['candidate']['risk_score']})")
    print(f"Final nudge: {final['candidate']['nudge']}")
    print(f"Verifier final: {final['verifier']}")
