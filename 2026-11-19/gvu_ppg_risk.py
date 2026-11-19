#!/usr/bin/env python3
"""
Minimal GVU prototype for dual-wavelength PPG glucose risk score.
Based on wearable finger PPG + MLP insight: dual-wavelength intensity features for non-invasive BGL estimation.
Generator produces risk score and band; Verifier checks clinical acceptability heuristic (score consistency with synthetic PPG features); Updater revises.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import json

@dataclass
class PPGSample:
    red_intensity: float  # 660 nm
    ir_intensity: float   # 880 nm
    ratio: float
    age: int
    bmi: float

def generate_candidate(sample: PPGSample, previous_critique: str = "") -> Dict:
    """Generator: produce risk score (0-100) and band based on dual-wavelength ratio + demographics."""
    # Simple heuristic proxy for MLP: higher IR/red ratio + higher BMI/age -> higher risk
    base_score = (sample.ratio - 0.8) * 50 + (sample.bmi - 25) * 1.0 + (sample.age - 40) * 0.3
    score = max(0, min(100, base_score + 25))
    if "boost" in previous_critique.lower() or "higher" in previous_critique.lower() or "too low" in previous_critique.lower():
        score = min(100, score + 25)
    band = "high" if score >= 70 else "moderate" if score >= 40 else "low"
    return {
        "risk_score": round(score, 1),
        "band": band,
        "features_used": ["dual_wavelength_ratio", "bmi", "age"],
        "rationale": f"Ratio {sample.ratio:.2f} with BMI {sample.bmi} suggests {band} risk."
    }

def verify(output: Dict, sample: PPGSample) -> Tuple[bool, str]:
    """Verifier: explicit criterion - score must be consistent with ratio > 1.1 implying elevated, and band matches score thresholds.
    Also require features include dual_wavelength.
    """
    score = output["risk_score"]
    band = output["band"]
    has_dual = "dual_wavelength_ratio" in output.get("features_used", [])
    consistent = True
    reason = ""
    if sample.ratio > 1.1 and score < 70:
        consistent = False
        reason = "High IR/red ratio (>1.1) but score too low; boost score."
    if band == "high" and score < 70 or band == "low" and score >= 40:
        consistent = False
        reason += " Band inconsistent with score thresholds."
    if not has_dual:
        consistent = False
        reason += " Missing dual-wavelength feature."
    passed = consistent and has_dual
    if not reason:
        reason = "Meets dual-wavelength consistency and band threshold criteria."
    return passed, reason

def updater_loop(sample: PPGSample, max_passes: int = 3) -> List[Dict]:
    logs = []
    critique = ""
    for i in range(1, max_passes + 1):
        candidate = generate_candidate(sample, critique)
        passed, reason = verify(candidate, sample)
        logs.append({
            "pass": i,
            "output": candidate,
            "passed": passed,
            "critique": reason
        })
        if passed:
            break
        critique = reason
    return logs

if __name__ == "__main__":
    # Smoke test sample: elevated risk (high ratio, higher BMI)
    sample = PPGSample(red_intensity=0.45, ir_intensity=0.62, ratio=1.38, age=55, bmi=31.2)
    logs = updater_loop(sample)
    print(json.dumps(logs, indent=2))
    # Final should pass on pass 2 typically
    assert any(l["passed"] for l in logs), "Should eventually pass"
    print("Smoke test complete. Final band:", logs[-1]["output"]["band"])
