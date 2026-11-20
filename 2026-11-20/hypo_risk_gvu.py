"""Minimal self-improving GVU agent for weekly hypoglycemia risk from CGM features.
Based on Cichosz et al. 2024 insight: LBGI/TBR/CV/GRADE from prior week predict next-week TBR>4%.
Verifier requires high-risk (TBR>4) to produce specific 15g nocturnal carb nudge, not generic.
"""

from typing import Dict, Any, List
import json

class Generator:
    def generate(self, features: Dict[str, float], critique: str = "") -> Dict[str, Any]:
        # Heuristic based on paper features: higher TBR, LBGI, CV -> higher risk
        tbr = features.get("tbr_prior", 0.0)
        lbgi = features.get("lbgi", 0.0)
        cv = features.get("cv", 0.0)
        grade = features.get("grade", 0.0)
        
        base_score = (tbr * 10) + (lbgi * 2) + (cv * 0.5) + (grade * 0.3)
        if "increase score" in critique.lower() or "higher risk" in critique.lower():
            base_score += 15
        if "specific nudge" in critique.lower() or "nocturnal" in critique.lower():
            nudge = "Take 15g complex carb at bedtime if TBR prior >4% to prevent nocturnal hypo."
        else:
            nudge = "Monitor closely and consider consulting clinician."
            
        risk_level = "high" if base_score > 70 else "moderate" if base_score > 40 else "low"
        
        return {
            "risk_score": round(base_score, 1),
            "risk_level": risk_level,
            "nudge": nudge,
            "features_used": list(features.keys())
        }

class Verifier:
    def verify(self, output: Dict[str, Any], features: Dict[str, float]) -> Dict[str, Any]:
        tbr = features.get("tbr_prior", 0.0)
        is_high_risk_case = tbr > 4.0
        score_ok = output["risk_score"] > 70 if is_high_risk_case else True
        nudge_specific = "15g" in output["nudge"].lower() and "nocturnal" in output["nudge"].lower() or "bedtime" in output["nudge"].lower()
        
        if is_high_risk_case and not (score_ok and nudge_specific):
            reason = "High TBR case requires risk_score >70 and specific 15g nocturnal/bedtime carb nudge."
            return {"pass": False, "reason": reason}
        return {"pass": True, "reason": "Meets criterion: specific actionable nudge for high-risk TBR."}

class Updater:
    def run(self, features: Dict[str, float], max_passes: int = 3) -> List[Dict[str, Any]]:
        gen = Generator()
        ver = Verifier()
        logs = []
        critique = ""
        for i in range(1, max_passes + 1):
            out = gen.generate(features, critique)
            check = ver.verify(out, features)
            log_entry = {"pass": i, "output": out, "verification": check}
            logs.append(log_entry)
            if check["pass"]:
                break
            critique = check["reason"] + " Increase score for high TBR and add specific nocturnal 15g carb."
        return logs

def smoke_test():
    sample = {"tbr_prior": 5.5, "lbgi": 3.2, "cv": 35.0, "grade": 12.0}  # high risk
    updater = Updater()
    results = updater.run(sample)
    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    smoke_test()
