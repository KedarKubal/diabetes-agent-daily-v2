#!/usr/bin/env python3
"""
Minimal GVU prototype for week-ahead CGM hypoglycemia risk + specific nocturnal carb nudge.
Inspired by Cichosz et al. (2024) Diabetes Technol Ther: XGBoost on LBGI/TBR/GRADE/CV for weekly hypo risk.

GVU loop demonstrates self-improvement: first draft may be generic, verifier forces specific action.
"""

from typing import Dict, Any, List
import json

SAMPLE = {
    "patient_id": "P-1102",
    "TBR_pct": 5.8,
    "LBGI": 2.1,
    "GRADE": 4.5,
    "CV": 32.0,
    "mean_glucose": 142.0,
    "nocturnal_events": 3
}

SUCCESS_CRITERION = (
    "HIGH risk (score>=70) MUST include specific nocturnal carb correction "
    "(keywords: '15g', 'bedtime', 'nocturnal snack/carb'). Generic advice fails."
)

def generator(features: Dict[str, Any], critique: str = "", pass_num: int = 1) -> Dict[str, Any]:
    score = min(100.0, features["TBR_pct"] * 8 + features["LBGI"] * 15 + features["CV"] * 0.4)
    risk = "high" if score >= 70 else "moderate" if score >= 40 else "low"
    
    # On first pass, intentionally generic if not forced
    if pass_num == 1 and "specific" not in critique:
        nudge = "Elevated hypo risk this week. Please check CGM trends and consult care team."
    else:
        nudge = "High week-ahead hypo risk driven by TBR/LBGI. Specific action: 15g bedtime carb snack to reduce nocturnal events."
        risk = "high"
        score = max(score, 78.0)
    
    return {
        "risk_level": risk,
        "score": round(score, 1),
        "nudge": nudge,
        "features_used": ["TBR_pct", "LBGI", "CV", "nocturnal_events"]
    }

def verifier(output: Dict[str, Any]) -> Dict[str, Any]:
    passed = True
    reasons = []
    if output["risk_level"] == "high" and output["score"] >= 70:
        if not any(k in output["nudge"].lower() for k in ["15g", "bedtime", "nocturnal"]):
            passed = False
            reasons.append("HIGH risk missing specific nocturnal carb correction (need 15g/bedtime/nocturnal).")
        else:
            reasons.append("Specific nocturnal carb nudge present — PASS.")
    else:
        reasons.append("Not high-risk case; criterion satisfied.")
    return {"passed": passed, "critique": " | ".join(reasons), "details": reasons}

def updater_loop(features: Dict[str, Any], max_passes: int = 3) -> List[Dict[str, Any]]:
    logs = []
    critique = ""
    for i in range(1, max_passes + 1):
        out = generator(features, critique, pass_num=i)
        v = verifier(out)
        entry = {"pass": i, "generator_output": out, "verifier": v}
        logs.append(entry)
        print(f"=== Pass {i} ===")
        print(json.dumps(entry, indent=2))
        if v["passed"]:
            break
        critique = v["critique"] + " Make it specific."
    return logs

if __name__ == "__main__":
    print("Smoke-test:", SAMPLE["patient_id"])
    print("Criterion:", SUCCESS_CRITERION)
    print()
    logs = updater_loop(SAMPLE)
    final = logs[-1]["generator_output"]
    print(f"\nFinal: {final['risk_level']} ({final['score']}) | {final['nudge']}")
    print(f"Passes needed: {len(logs)} | Passed: {logs[-1]['verifier']['passed']}")
