#!/usr/bin/env python3
"""
Minimal GVU prototype: Hypoglycemia risk flag from CGM trend.
Generator produces risk score/flag; Verifier critiques against explicit criterion;
Updater loops with feedback.
"""

from typing import Dict, List, Tuple
import json

# Sample CGM data: list of (timestamp_offset_min, glucose_mg_dl)
SAMPLE_CGM = [
    (0, 120), (5, 115), (10, 108), (15, 95), (20, 82),
    (25, 70), (30, 62), (35, 55), (40, 48)
]

def generator(cgm: List[Tuple[int, int]], critique: str = "") -> Dict:
    """Generator: simple heuristic risk from recent lows and slope."""
    if not cgm:
        return {"risk": "unknown", "score": 0.0, "reason": "no data"}
    
    recent = cgm[-5:]  # last 25 min
    lows = sum(1 for _, g in recent if g < 70)
    slope = (recent[-1][1] - recent[0][1]) / max(1, len(recent)-1)
    
    score = min(1.0, lows * 0.3 + max(0, -slope) * 0.1)
    risk = "high" if score > 0.6 or (recent[-1][1] < 60) else "medium" if score > 0.3 else "low"
    
    # Incorporate critique if present
    if "more conservative" in critique.lower() or "false positive" in critique.lower():
        score *= 0.7
        risk = "high" if score > 0.5 else "medium" if score > 0.2 else "low"
    elif "too lenient" in critique.lower():
        score = min(1.0, score * 1.3)
        risk = "high" if score > 0.5 else "medium" if score > 0.25 else "low"
    
    return {
        "risk": risk,
        "score": round(score, 3),
        "lows_count": lows,
        "slope": round(slope, 2),
        "reason": f"Based on {lows} lows in recent window, slope {slope:.1f}. {critique[:50]}"
    }

def verifier(output: Dict, cgm: List[Tuple[int, int]]) -> Tuple[bool, str]:
    """Verifier: explicit criterion - high risk if any glucose <55 or 3+ lows <70 in last 30min."""
    if not cgm:
        return False, "no data"
    
    recent = [g for _, g in cgm if _ >= cgm[-1][0] - 30]
    severe = any(g < 55 for g in recent)
    multiple_lows = sum(1 for g in recent if g < 70) >= 3
    
    expected_high = severe or multiple_lows
    actual_high = output["risk"] == "high"
    
    if expected_high and not actual_high:
        return False, "too lenient: should flag high given severe/multiple lows"
    if not expected_high and actual_high and output["score"] > 0.7:
        return False, "more conservative: over-flagging without strong evidence"
    return True, "matches criterion"

def updater_loop(cgm: List[Tuple[int, int]], passes: int = 3) -> List[Dict]:
    """Run GVU loop, log each pass."""
    logs = []
    critique = ""
    for i in range(passes):
        gen_out = generator(cgm, critique)
        passed, reason = verifier(gen_out, cgm)
        log = {
            "pass": i+1,
            "generator": gen_out,
            "verifier_pass": passed,
            "critique": reason
        }
        logs.append(log)
        critique = reason  # feed back
        if passed:
            break
    return logs

if __name__ == "__main__":
    print("=== GVU Hypo Risk Nudge Prototype ===")
    results = updater_loop(SAMPLE_CGM)
    for r in results:
        print(json.dumps(r, indent=2))
    print("\nFinal output:", results[-1]["generator"])
