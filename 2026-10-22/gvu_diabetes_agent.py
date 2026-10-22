#!/usr/bin/env python3
"""
Minimal self-improving multi-agent prototype (Generator-Verifier-Updater)
for explainable CGM-based hypoglycemia/hyperglycemia risk prediction.

Based on: Explainable ML for real-time hypo/hyper prediction (Duckworth et al.)
Core insight: SHAP-style feature attributions turn black-box risk scores into
actionable, personalized explanations that can reduce alarm fatigue.

Verifier success criterion (explicit & falsifiable):
  1. Risk score in [0, 100]
  2. Explanation must cite at least one concrete CGM feature (e.g., recent_slope,
     time_below_range, mean_glucose) AND propose one specific action.
  3. If risk >= 70, explanation must include a concrete mitigation (carb amount or timing).

Logs each pass so the improvement is visible.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import json

@dataclass
class Sample:
    patient_id: str
    recent_glucose: List[float]  # last 12 readings, mg/dL, 5-min
    mean_24h: float
    time_below_70_pct: float
    recent_slope: float  # mg/dL per hour
    last_carb_g: float
    iob: float  # insulin on board, units

def generator(sample: Sample, critique: str = "") -> Dict[str, Any]:
    """Generator agent: produces risk score + explanation."""
    # Simple heuristic features (stand-in for the XGBoost + SHAP of the paper)
    slope_penalty = max(0, -sample.recent_slope) * 2.0
    tbr_penalty = sample.time_below_70_pct * 1.5
    low_recent = 70 - min(sample.recent_glucose[-3:]) if min(sample.recent_glucose[-3:]) < 70 else 0
    score = min(100, max(0, 40 + slope_penalty + tbr_penalty + low_recent * 0.8 - sample.last_carb_g * 0.3))

    features_cited = []
    if abs(sample.recent_slope) > 20:
        features_cited.append(f"recent_slope={sample.recent_slope:.1f} mg/dL/h")
    if sample.time_below_70_pct > 5:
        features_cited.append(f"time_below_70={sample.time_below_70_pct:.1f}%")
    if sample.mean_24h > 180 or sample.mean_24h < 100:
        features_cited.append(f"mean_24h={sample.mean_24h:.0f}")

    action = "Continue routine monitoring."
    if score >= 70:
        action = "Take 15 g fast-acting carbohydrate now and recheck in 15 min."
    elif score >= 50:
        action = "Have a small snack (10-15 g carb) within the next 30 min."

    # Incorporate critique if provided
    if "missing concrete feature" in critique.lower():
        features_cited.append(f"recent_glucose_min={min(sample.recent_glucose):.0f}")
    if "missing mitigation" in critique.lower() and score >= 70:
        action = "Take 15 g fast-acting carbohydrate now and recheck in 15 min."

    explanation = (
        f"Risk drivers: {', '.join(features_cited) or 'stable pattern'}. "
        f"Recommended action: {action}"
    )

    return {
        "risk_score": round(score, 1),
        "explanation": explanation,
        "features_cited": features_cited,
        "action": action,
    }

def verifier(output: Dict[str, Any], sample: Sample) -> Dict[str, Any]:
    """Verifier agent: checks against explicit success criterion."""
    reasons = []
    passed = True

    if not (0 <= output["risk_score"] <= 100):
        reasons.append("score out of [0,100]")
        passed = False

    has_feature = any(
        k in output["explanation"].lower()
        for k in ["slope", "time_below", "mean_24h", "recent_glucose"]
    )
    if not has_feature:
        reasons.append("missing concrete feature")
        passed = False

    has_action = "carb" in output["explanation"].lower() or "snack" in output["explanation"].lower() or "monitor" in output["explanation"].lower()
    if not has_action:
        reasons.append("missing action")
        passed = False

    if output["risk_score"] >= 70 and "15 g" not in output["explanation"]:
        reasons.append("missing mitigation")
        passed = False

    return {
        "pass": passed,
        "reasons": reasons if reasons else ["ok"],
        "critique": "; ".join(reasons) if reasons else "",
    }

def updater_loop(sample: Sample, max_passes: int = 3) -> List[Dict[str, Any]]:
    """Updater loop: Generator → Verifier → critique → revise."""
    log = []
    critique = ""
    for i in range(1, max_passes + 1):
        out = generator(sample, critique)
        ver = verifier(out, sample)
        entry = {
            "pass": i,
            "output": out,
            "verifier": ver,
        }
        log.append(entry)
        if ver["pass"]:
            break
        critique = ver["critique"]
    return log

def smoke_test():
    sample = Sample(
        patient_id="P-2210",
        recent_glucose=[145, 138, 122, 110, 98, 85, 78, 72, 68, 65, 62, 60],
        mean_24h=155,
        time_below_70_pct=8.2,
        recent_slope=-45.0,
        last_carb_g=0,
        iob=1.2,
    )
    print("=== Smoke test: high-risk declining CGM ===")
    results = updater_loop(sample)
    for r in results:
        print(f"Pass {r['pass']}: score={r['output']['risk_score']} | {r['output']['explanation']}")
        print(f"  Verifier: {'PASS' if r['verifier']['pass'] else 'FAIL'} — {r['verifier']['reasons']}")
    print("\nFinal output:", json.dumps(results[-1]["output"], indent=2))
    return results

if __name__ == "__main__":
    smoke_test()
