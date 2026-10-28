"""Minimal GVU prototype for week-ahead hypoglycemia risk from CGM features.
Based on underexploited insight from Cichosz et al. 2024: feature-engineered
XGBoost on LBGI, TBR, GRADE, CV, waveform length for weekly TBR>4% prediction.
Smoke-test generates risk score + specific nocturnal nudge, verifies against
explicit criterion (score>=70 and nudge mentions carb correction if TBR>4), loops 2-3x.
"""

import json
from typing import Dict, Any, List

def generator(features: Dict[str, float], critique: str = "") -> Dict[str, Any]:
    """Generate candidate risk score and nudge."""
    lbgi = features.get("lbgi", 0.0)
    tbr = features.get("tbr", 0.0)
    cv = features.get("cv", 0.0)
    grade = features.get("grade", 0.0)
    
    # Simple heuristic score inspired by paper features (higher = higher risk)
    score = min(100.0, 40 + lbgi * 8 + tbr * 6 + cv * 1.5 + grade * 0.5)
    
    if critique:
        # Updater logic: boost if critique mentions missing nocturnal
        if "nocturnal" in critique.lower() or "carb" in critique.lower():
            score = min(100.0, score + 15)
            nudge = "High risk: schedule 15g complex carb at bedtime and check CGM at 3am."
        else:
            nudge = "Moderate risk: monitor trends and adjust basal if pattern continues."
    else:
        if tbr > 4.0:
            nudge = "Elevated weekly hypo risk detected from prior TBR."
        else:
            nudge = "Low risk this week; continue current management."
    
    return {"risk_score": round(score, 1), "nudge": nudge, "features_used": list(features.keys())}

def verifier(output: Dict[str, Any], features: Dict[str, float]) -> Dict[str, Any]:
    """Explicit success criterion: score >=70 AND if TBR>4 then nudge must mention carb/nocturnal."""
    score = output.get("risk_score", 0)
    nudge = output.get("nudge", "").lower()
    tbr = features.get("tbr", 0)
    
    passed = score >= 70.0
    reason = f"Score {score} "
    if tbr > 4.0:
        if "carb" not in nudge and "nocturnal" not in nudge and "bedtime" not in nudge:
            passed = False
            reason += "failed: high TBR but no specific carb/nocturnal correction in nudge."
        else:
            reason += "passed with specific correction."
    else:
        reason += "passed (TBR not elevated)."
    
    return {"passed": passed, "reason": reason}

def gvu_loop(features: Dict[str, float], max_passes: int = 3) -> List[Dict[str, Any]]:
    """Run Generator-Verifier-Updater loop, log each pass."""
    log = []
    critique = ""
    for i in range(1, max_passes + 1):
        out = generator(features, critique)
        ver = verifier(out, features)
        entry = {"pass": i, "output": out, "verification": ver}
        log.append(entry)
        if ver["passed"]:
            break
        critique = ver["reason"]  # feed back for updater
    return log

if __name__ == "__main__":
    # Sample high-risk week (from typical paper cohort stats)
    sample = {"lbgi": 3.2, "tbr": 5.5, "cv": 38.0, "grade": 12.4}
    results = gvu_loop(sample)
    print(json.dumps(results, indent=2))
    with open("2026-10-28/smoke_test.json", "w") as f:
        json.dump({"sample": sample, "results": results}, f, indent=2)
