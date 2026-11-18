"""Minimal self-improving GVU agent for hypoglycemia risk flagging.
Based on multi-task learning insight: joint glucose forecast + hypo classification,
with critique-driven refinement.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
import json

@dataclass
class AgentOutput:
    risk_level: str  # LOW, MODERATE, HIGH
    score: float
    nudge: str
    features_used: List[str]
    pass_num: int

class Generator:
    def __init__(self):
        self.history = []

    def generate(self, sample: Dict[str, Any], critique: str = "") -> AgentOutput:
        tbr = sample.get("tbr", 0.0)
        slope = sample.get("slope", 0.0)
        iob = sample.get("iob", 0.0)
        nocturnal = sample.get("nocturnal", False)
        
        # Base heuristic from multi-task style: combine slope + TBR
        score = min(100.0, max(0.0, 40 + tbr * 8 - slope * 15 + iob * 5))
        if nocturnal:
            score += 10
        
        risk = "LOW" if score < 40 else "MODERATE" if score < 70 else "HIGH"
        
        # Incorporate critique if present
        if "specific" in critique.lower() or "carb" in critique.lower():
            nudge = "15g fast-acting carb at bedtime + check in 15 min"
            features_used = ["tbr", "slope", "iob", "nocturnal", "specific_nudge"]
        else:
            nudge = "Monitor closely and consider snack if trending low"
            features_used = ["tbr", "slope", "iob", "nocturnal"]
        
        # Adjust score slightly on critique
        if "higher" in critique.lower() or "high" in critique.lower():
            score = min(100, score + 15)
            risk = "HIGH" if score >= 70 else risk
        
        out = AgentOutput(risk, round(score, 1), nudge, features_used, len(self.history) + 1)
        self.history.append(out)
        return out

class Verifier:
    def verify(self, output: AgentOutput, sample: Dict[str, Any]) -> Dict[str, Any]:
        tbr = sample.get("tbr", 0)
        slope = sample.get("slope", 0)
        nocturnal = sample.get("nocturnal", False)
        
        # Explicit success criteria: high-risk nocturnal with negative slope must have HIGH risk + specific 15g carb nudge
        is_high_risk_case = nocturnal and slope < -1.0 and tbr > 4.0
        has_specific_nudge = "15g" in output.nudge and "carb" in output.nudge.lower()
        has_high_risk = output.risk_level == "HIGH" and output.score >= 70
        
        passed = True
        reasons = []
        if is_high_risk_case:
            if not has_high_risk:
                passed = False
                reasons.append("High-risk nocturnal case requires HIGH risk level and score >=70")
            if not has_specific_nudge:
                passed = False
                reasons.append("Must include specific 15g carb bedtime nudge for nocturnal hypo risk")
        
        return {
            "pass": passed,
            "reasons": reasons if not passed else ["Meets explicit criteria: HIGH risk + specific 15g carb for nocturnal high-risk"],
            "criteria": "For nocturnal + slope<-1 + TBR>4: must be HIGH + 15g carb nudge"
        }

class Updater:
    def __init__(self, generator: Generator, verifier: Verifier):
        self.generator = generator
        self.verifier = verifier
        self.logs = []

    def run_loop(self, sample: Dict[str, Any], max_passes: int = 3) -> List[Dict]:
        critique = ""
        results = []
        for i in range(max_passes):
            out = self.generator.generate(sample, critique)
            ver = self.verifier.verify(out, sample)
            entry = {
                "pass": i + 1,
                "output": {
                    "risk_level": out.risk_level,
                    "score": out.score,
                    "nudge": out.nudge,
                    "features_used": out.features_used
                },
                "verifier": ver
            }
            results.append(entry)
            self.logs.append(entry)
            if ver["pass"]:
                break
            # Build critique for next pass
            critique = " ".join(ver["reasons"]) + ". Increase specificity and risk for nocturnal cases."
        return results

def smoke_test():
    sample = {
        "patient_id": "P-1118",
        "tbr": 5.8,
        "slope": -1.5,
        "iob": 1.2,
        "nocturnal": True,
        "notes": "High nocturnal TBR with negative slope"
    }
    gen = Generator()
    ver = Verifier()
    updater = Updater(gen, ver)
    results = updater.run_loop(sample)
    return {
        "sample": sample,
        "gvu_results": results,
        "final_pass": results[-1]["verifier"]["pass"]
    }

if __name__ == "__main__":
    result = smoke_test()
    print(json.dumps(result, indent=2))
    with open("smoke_test_result.json", "w") as f:
        json.dump(result, f, indent=2)
