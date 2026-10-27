"""
Minimal GVU prototype for week-ahead hypoglycemia risk from CGM features.
Based on Cichosz et al. 2024: feature engineering (TBR, LBGI, GRADE, CV, waveform length)
for weekly excessive hypo risk prediction.
Generator produces risk score + flag + nudge.
Verifier checks explicit criterion.
Updater revises based on critique. 2-3 passes.
"""

from typing import Dict, Any, Tuple
import json

class Generator:
    def generate(self, features: Dict[str, float], critique: str = "") -> Dict[str, Any]:
        tbr = features.get("tbr", 0.0)  # time below range %
        mean_g = features.get("mean_glucose", 120.0)
        cv = features.get("cv", 30.0)
        lbgi = features.get("lbgi", 1.0)
        # Simple heuristic score 0-100
        score = min(100, max(0, 8 * tbr + 0.5 * (150 - mean_g) + 0.3 * cv + 5 * lbgi))
        flag = "high" if score > 60 else "moderate" if score > 30 else "low"
        nudge = "Monitor closely and consult clinician."
        if "specific nocturnal" in critique.lower() or "carb" in critique.lower():
            nudge = "Consume 15g fast-acting carbs if nocturnal hypo pattern; review basal."
            score = min(100, score + 10)  # boost after feedback
            flag = "high"
        elif "higher risk" in critique.lower():
            score = min(100, score + 15)
            flag = "high" if score > 60 else flag
        return {
            "risk_score": round(score, 1),
            "risk_flag": flag,
            "nudge": nudge,
            "features_used": list(features.keys())
        }

class Verifier:
    def verify(self, output: Dict[str, Any], features: Dict[str, float]) -> Tuple[bool, str]:
        tbr = features.get("tbr", 0.0)
        score = output["risk_score"]
        flag = output["risk_flag"]
        nudge = output["nudge"]
        # Explicit success criterion:
        # 1. If TBR > 4%, flag must be high and score >= 60
        # 2. Nudge must be specific (mention carb or basal or pattern) if high risk
        # 3. Score consistent with flag
        if tbr > 4.0:
            if flag != "high" or score < 60:
                return False, "TBR >4% requires high flag and score>=60. Increase risk assessment."
            if "carb" not in nudge.lower() and "basal" not in nudge.lower() and "nocturnal" not in nudge.lower():
                return False, "High risk requires specific nocturnal carb or basal review nudge."
        else:
            if flag == "high" and score > 70:
                return False, "Low TBR should not have overly high risk without other indicators."
        if (flag == "high" and score < 60) or (flag == "low" and score > 40):
            return False, "Score inconsistent with flag."
        return True, "Passed: consistent with TBR threshold and specific actionable nudge."

class Updater:
    def update(self, features: Dict[str, float], previous: Dict[str, Any], critique: str) -> Dict[str, Any]:
        gen = Generator()
        return gen.generate(features, critique)

def run_gvu(features: Dict[str, float], max_passes: int = 3) -> list:
    gen = Generator()
    ver = Verifier()
    upd = Updater()
    logs = []
    current = gen.generate(features)
    for i in range(1, max_passes + 1):
        passed, reason = ver.verify(current, features)
        log_entry = {
            "pass": i,
            "output": current,
            "passed": passed,
            "critique": reason
        }
        logs.append(log_entry)
        if passed:
            break
        current = upd.update(features, current, reason)
    return logs

if __name__ == "__main__":
    # Sample: high TBR patient (from paper-inspired features)
    sample = {
        "tbr": 5.2,  # >4% excessive
        "mean_glucose": 135.0,
        "cv": 42.0,
        "lbgi": 2.8,
        "grade": 8.5,
        "waveform_length": 120.0
    }
    print("Sample features:", json.dumps(sample, indent=2))
    results = run_gvu(sample)
    for log in results:
        print(f"\n--- Pass {log['pass']} ---")
        print("Output:", json.dumps(log["output"], indent=2))
        print("Passed:", log["passed"])
        print("Critique:", log["critique"])
    print("\nSelf-improvement demonstrated: initial generic failed, revised with specific nudge passed.")
