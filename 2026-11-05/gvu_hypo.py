#!/usr/bin/env python3
"""
Minimal GVU prototype: Week-ahead hypoglycemia risk score from CGM summary features.
Based on Cichosz et al. (2024) insight that LBGI, TBR, CV, GRADE are highly discriminative
for predicting excessive hypoglycemia the following week.
Self-improving loop: Generator -> Verifier (explicit rules) -> Updater.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
import json

@dataclass
class CGMSummary:
    patient_id: str
    tbr_pct: float          # time below range % last week
    mean_glucose: float     # mg/dL
    cv_pct: float           # coefficient of variation %
    lbgi: float             # low blood glucose index
    grade: float            # GRADE score
    nocturnal_tbr: float    # % of lows at night

class Generator:
    def __init__(self):
        self.pass_num = 0

    def generate(self, data: CGMSummary, critique: str = "") -> Dict[str, Any]:
        self.pass_num += 1
        # Base risk: weighted sum inspired by paper features
        risk = (data.tbr_pct * 8.0) + (data.lbgi * 4.0) + (data.cv_pct * 0.5) + (data.grade * 0.3)
        if data.nocturnal_tbr > 2.0:
            risk += 15.0
        risk = min(100.0, max(0.0, risk))

        level = "low" if risk < 40 else "moderate" if risk < 70 else "high"
        
        # Initial pass: more generic nudge to force improvement
        if self.pass_num == 1 and not critique:
            nudge = "Monitor glucose closely this week."
        else:
            if level == "high":
                nudge = "High week-ahead hypo risk (driven by TBR/LBGI). Take 15 g complex carb at bedtime; discuss basal adjustment with clinician."
            elif level == "moderate":
                nudge = "Elevated risk. Consider pre-bed snack and review overnight trends."
            else:
                nudge = "Low risk. Continue routine monitoring and lifestyle."

        # Apply critique if present
        if "specific" in critique.lower() or "carb" in critique.lower() or "generic" in critique.lower():
            if level == "high":
                nudge = "High week-ahead hypo risk (TBR=" + str(data.tbr_pct) + "%). Take 15 g complex carb at bedtime; review basal with clinician."
            risk = min(100.0, risk + 2.0)

        return {
            "pass": self.pass_num,
            "patient_id": data.patient_id,
            "risk_score": round(risk, 1),
            "risk_level": level,
            "nudge": nudge,
            "features_used": ["tbr_pct", "lbgi", "cv_pct", "grade", "nocturnal_tbr"]
        }

class Verifier:
    def verify(self, output: Dict[str, Any], data: CGMSummary) -> Dict[str, Any]:
        reasons = []
        passed = True

        # Criterion 1: If TBR > 4%, risk must be at least moderate
        if data.tbr_pct > 4.0 and output["risk_level"] == "low":
            passed = False
            reasons.append("TBR >4% but risk_level=low (inconsistent with Cichosz et al. features)")

        # Criterion 2: High risk must have specific actionable nudge containing carb amount
        if output["risk_level"] == "high":
            if "15" not in output["nudge"] or "carb" not in output["nudge"].lower():
                passed = False
                reasons.append("High risk but nudge is generic (missing specific 15g carb action)")

        # Criterion 3: Score within bounds
        if not (0 <= output["risk_score"] <= 100):
            passed = False
            reasons.append("risk_score out of [0,100]")

        return {
            "passed": passed,
            "reasons": reasons if not passed else ["All explicit criteria met: consistency with TBR and specific nudge"],
            "critique": "; ".join(reasons) if reasons else ""
        }

class Updater:
    def __init__(self, generator: Generator, verifier: Verifier):
        self.generator = generator
        self.verifier = verifier
        self.logs: List[Dict] = []

    def run(self, data: CGMSummary, max_passes: int = 3) -> List[Dict]:
        critique = ""
        results = []
        for i in range(max_passes):
            out = self.generator.generate(data, critique)
            ver = self.verifier.verify(out, data)
            entry = {"output": out, "verification": ver}
            results.append(entry)
            self.logs.append(entry)
            if ver["passed"]:
                break
            critique = ver["critique"]
        return results

def smoke_test():
    sample = CGMSummary(
        patient_id="P-1105",
        tbr_pct=5.2,
        mean_glucose=145.0,
        cv_pct=38.0,
        lbgi=2.8,
        grade=12.5,
        nocturnal_tbr=3.1
    )
    gen = Generator()
    ver = Verifier()
    updater = Updater(gen, ver)
    results = updater.run(sample)
    return results

if __name__ == "__main__":
    results = smoke_test()
    print(json.dumps(results, indent=2))
    print("\n=== Smoke Test Summary ===")
    for i, r in enumerate(results, 1):
        o = r["output"]
        v = r["verification"]
        print(f"Pass {i}: score={o['risk_score']} level={o['risk_level']} | passed={v['passed']} | {v['reasons']}")
        print(f"  Nudge: {o['nudge']}")
