#!/usr/bin/env python3
"""
Minimal Generator-Verifier-Updater (GVU) prototype for week-ahead hypoglycemia risk
from synthetic CGM summary features. Based on the underexploited insight from
Cichosz et al. (2024): engineered CGM features (LBGI, TBR, CV, waveform length)
predict weekly excessive hypo risk.
"""

from typing import Dict, Any, List

SAMPLE = {
    "patient_id": "P-1410",
    "mean_glucose": 142.0,
    "cv": 0.38,
    "tbr": 0.06,
    "lbgi": 2.8,
    "waveform_length": 1450.0,
    "grade": 4.2,
}

def generator(features: Dict[str, float], critique: str = "") -> Dict[str, Any]:
    """Generator produces candidate risk + nudge."""
    base = features["lbgi"] * 12 + features["tbr"] * 250 + features["cv"] * 40
    risk_score = min(100.0, base)
    flag = "high" if risk_score > 55 else "moderate" if risk_score > 30 else "low"
    nudge = "Monitor glucose more closely this week."
    
    if critique:
        if "nocturnal" in critique.lower() or "specific" in critique.lower():
            risk_score = min(100.0, risk_score + 8)
            flag = "high" if risk_score > 50 else flag
            nudge = "Prioritize nocturnal carb correction (15 g) and review basal rates; track LBGI next week."
        if "waveform" in critique.lower():
            risk_score = min(100.0, risk_score + features["waveform_length"] / 200.0)
    
    return {
        "risk_score": round(risk_score, 1),
        "flag": flag,
        "nudge": nudge,
        "features_used": ["lbgi", "tbr", "cv"] + (["waveform_length"] if "waveform" in critique.lower() else []),
    }

def verifier(output: Dict[str, Any], features: Dict[str, float]) -> Dict[str, Any]:
    """Success criterion: flag correctly reflects elevated TBR/LBGI AND nudge is actionable/specific."""
    tbr, lbgi = features["tbr"], features["lbgi"]
    flag = output["flag"]
    nudge = output["nudge"].lower()
    
    expected_high = tbr > 0.04 and lbgi > 2.0
    risk_ok = (expected_high and flag == "high") or (not expected_high and flag != "high")
    specific = any(k in nudge for k in ["nocturnal", "15 g", "basal rates", "carb correction"])
    
    passed = risk_ok and specific
    reasons = []
    if not risk_ok:
        reasons.append(f"flag '{flag}' mismatches expected high-risk (tbr={tbr}, lbgi={lbgi})")
    if not specific:
        reasons.append("nudge lacks specificity (needs nocturnal/carb/basal detail)")
    
    return {"passed": passed, "reason": "; ".join(reasons) or "Criteria satisfied.", "risk_ok": risk_ok, "specific": specific}

def updater_loop(features: Dict[str, float], max_passes: int = 3) -> List[Dict[str, Any]]:
    history = []
    critique = ""
    for pass_num in range(1, max_passes + 1):
        out = generator(features, critique)
        ver = verifier(out, features)
        history.append({"pass": pass_num, "output": out, "verifier": ver, "critique": critique})
        if ver["passed"]:
            break
        critique = ver["reason"] + " \u2014 increase nocturnal focus and include waveform if useful"
    return history

if __name__ == "__main__":
    print("=== GVU Week-Ahead Hypo Risk (2026-10-14) ===")
    print(f"Patient: {SAMPLE['patient_id']}")
    history = updater_loop(SAMPLE)
    for rec in history:
        print(f"\nPass {rec['pass']}: risk={rec['output']['risk_score']} flag={rec['output']['flag']}")
        print(f"  Nudge: {rec['output']['nudge']}")
        print(f"  Verifier: {'PASS' if rec['verifier']['passed'] else 'FAIL'} \u2014 {rec['verifier']['reason']}")
    print("\nDone.")
