#!/usr/bin/env python3
"""
Minimal GVU prototype for unconstrained wearable prediabetes detection opportunity.
Generator: produces candidate risk score + label from mock features.
Verifier: checks against explicit criterion (score consistency with feature pattern).
Updater: loops 2-3 times feeding critique.
"""

from typing import Dict, Any, Tuple

# Sample input features inspired by dynamic model + glucose curve features (high risk)
SAMPLE_FEATURES = {
    "mean_glucose": 108.0,
    "glucose_variability": 18.0,  # moderate
    "inertial_activity_score": 0.6,
    "curve_peak_delta": 42.0,
    "recovery_slope": -0.8,
    "bootstrap_conf": 0.75
}

def generator(features: Dict[str, float], critique: str = "") -> Dict[str, Any]:
    """Produces candidate output: risk score, label, rationale."""
    # Base calculation that may under-estimate initially
    base_score = 0.40 + (features["mean_glucose"] - 100) / 80 + features["curve_peak_delta"] / 200 - features["inertial_activity_score"] * 0.1
    base_score = min(max(base_score, 0.0), 1.0)
    
    if "insufficient" in critique.lower() or "fail" in critique.lower():
        base_score = min(base_score + 0.20, 1.0)
    
    label = "prediabetes" if base_score >= 0.65 else "normoglycemia"
    rationale = f"Score {base_score:.2f} from mean={features['mean_glucose']}, peak_delta={features['curve_peak_delta']}, activity={features['inertial_activity_score']}"
    if critique:
        rationale += f" | Revised: boosted after critique"
    
    return {
        "risk_score": round(base_score, 2),
        "label": label,
        "rationale": rationale,
        "features_used": list(features.keys())
    }

def verifier(output: Dict[str, Any], features: Dict[str, float]) -> Tuple[bool, str]:
    """Explicit success criterion: high-risk pattern (mean>105 and peak_delta>40) requires label=prediabetes and score>=0.70."""
    high_risk_pattern = features["mean_glucose"] > 105 and features["curve_peak_delta"] > 40
    if high_risk_pattern:
        passed = output["label"] == "prediabetes" and output["risk_score"] >= 0.70
        reason = "PASS: high-risk pattern correctly flagged as prediabetes >=0.70" if passed else "FAIL: high-risk pattern but score/label insufficient (need >=0.70 prediabetes)"
    else:
        passed = True
        reason = "PASS: not high-risk pattern"
    return passed, reason

def updater_loop(features: Dict[str, float], max_passes: int = 3) -> list:
    """Runs GVU loop, logs each pass."""
    logs = []
    critique = ""
    for pass_num in range(1, max_passes + 1):
        candidate = generator(features, critique)
        passed, reason = verifier(candidate, features)
        log_entry = {
            "pass": pass_num,
            "output": candidate,
            "passed": passed,
            "critique": reason
        }
        logs.append(log_entry)
        print(f"Pass {pass_num}: score={candidate['risk_score']}, label={candidate['label']}, passed={passed}")
        print(f"  Reason: {reason}")
        if passed:
            break
        critique = reason
    return logs

if __name__ == "__main__":
    print("=== Smoke test: unconstrained wearable prediabetes GVU ===")
    results = updater_loop(SAMPLE_FEATURES)
    print("\n=== Before (pass 1) / After (final) ===")
    if len(results) > 1:
        print("Before:", results[0]["output"])
        print("After:", results[-1]["output"])
    else:
        print(results[-1]["output"])
