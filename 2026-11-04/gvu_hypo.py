"""Minimal Generator-Verifier-Updater loop for explainable CGM hypoglycemia risk + personalized nudge.
Prototypes the underexploited insight from Duckworth et al. 2024: SHAP-style feature attributions
turned into concrete, verifiable 60-minute recommendations.
"""

from typing import Dict, Tuple, List
import json

# Sample CGM-derived features (simulating SHAP-attributed inputs)
SAMPLE = {
    "patient_id": "P-1104",
    "tbr_nocturnal_pct": 6.2,          # time below range 00:00-06:00
    "slope_30min": -1.8,               # mg/dL per min
    "mean_glucose_24h": 142,
    "cv_7d": 34.5,
    "lbgi": 2.1
}

def generator(features: Dict, critique: str = "") -> Dict:
    """Produce candidate risk score, level, and nudge."""
    score = 40
    if features["tbr_nocturnal_pct"] > 5:
        score += 35
    if features["slope_30min"] < -1.5:
        score += 20
    if features["cv_7d"] > 30:
        score += 10
    score = min(100, score)

    level = "high" if score >= 70 else "moderate" if score >= 40 else "low"

    # Base nudge
    if features["tbr_nocturnal_pct"] > 5 or features["slope_30min"] < -1.5:
        nudge = (
            f"High nocturnal hypo risk driven by TBR {features['tbr_nocturnal_pct']}% "
            f"and slope {features['slope_30min']} mg/dL/min. Take 15 g carbohydrate at bedtime."
        )
    else:
        nudge = (
            f"Moderate risk. Monitor closely; CV {features['cv_7d']}% suggests variability. "
            "Consider earlier dinner or light activity."
        )

    # Incorporate critique if present (simple string append for demo)
    if critique:
        nudge += f" [Revised per critique: {critique}]"

    return {
        "score": score,
        "level": level,
        "nudge": nudge,
        "features_used": list(features.keys())
    }

def verifier(output: Dict, features: Dict) -> Tuple[bool, str]:
    """Explicit success criterion."""
    if not isinstance(output.get("score"), (int, float)) or not (0 <= output["score"] <= 100):
        return False, "score not numeric in [0,100]"

    nocturnal_risk = features["tbr_nocturnal_pct"] > 5 or features["slope_30min"] < -1.5
    nudge = output.get("nudge", "").lower()

    if nocturnal_risk:
        if "15 g" in nudge and ("bedtime" in nudge or "nocturnal" in nudge):
            return True, "passed: nocturnal risk correctly addressed with 15 g carb"
        else:
            return False, "nocturnal risk present but nudge missing 15 g carbohydrate + bedtime/nocturnal"
    else:
        if any(f.lower() in nudge for f in ["cv", "slope", "tbr", "glucose"]):
            return True, "passed: non-nocturnal nudge references at least one feature"
        else:
            return False, "nudge is generic; must reference at least one input feature"

def updater(features: Dict, max_passes: int = 3) -> List[Dict]:
    """Run GVU loop, logging each pass."""
    log = []
    critique = ""
    for i in range(1, max_passes + 1):
        candidate = generator(features, critique)
        passed, reason = verifier(candidate, features)
        entry = {
            "pass": i,
            "output": candidate,
            "passed": passed,
            "reason": reason
        }
        log.append(entry)
        if passed:
            break
        critique = reason  # feed back for next generation
    return log

if __name__ == "__main__":
    print("=== HypoNudge-GVU smoke test ===")
    print(f"Sample features: {json.dumps(SAMPLE, indent=2)}")
    results = updater(SAMPLE)
    for r in results:
        print(f"\n--- Pass {r['pass']} ---")
        print(f"Score/Level: {r['output']['score']} / {r['output']['level']}")
        print(f"Nudge: {r['output']['nudge']}")
        print(f"Verifier: {'PASS' if r['passed'] else 'FAIL'} — {r['reason']}")
    print("\n=== Done ===")
