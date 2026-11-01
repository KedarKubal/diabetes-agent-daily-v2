#!/usr/bin/env python3
"""
Minimal GVU prototype for personalized ISF/ICR extraction via iterative refinement.
Based on the insight from Temporal Transformer personalization of insulin params from CGM/pump data
(e.g., attention mechanisms extracting invariant ISF/ICR).
Generator proposes params, Verifier checks explicit stability + variance criterion,
Updater feeds critique to refine. 2-3 passes.
"""

import json
from typing import Dict, Tuple, List

SAMPLE_DATA = {
    "patient_id": "P-1101",
    "mean_glucose": 145.0,
    "std_glucose": 52.0,
    "carb_events": 4.2,
    "insulin_units": 28.0,
    "hypo_events_week": 2.1,
    "hyper_events_week": 3.5
}

SUCCESS_CRITERION = {
    "max_predicted_std": 40.0,
    "isf_range": (40, 120),
}

class Generator:
    def __init__(self):
        self.history = []
    
    def generate(self, data: Dict, critique: str = "") -> Dict:
        base_isf = 1800 / data["insulin_units"]
        base_icr = 500 / data["insulin_units"]
        
        # Refinement factor from critique
        factor = 1.0
        if "high variance" in critique.lower() or "pred_std" in critique.lower():
            factor = 1.2  # increase sensitivity to reduce variance
        if "hypo" in critique.lower() and "not reduced" in critique.lower():
            factor = 0.85
        
        isf = round(max(40, min(120, base_isf * factor)), 1)
        icr = round(max(5, min(30, base_icr * factor * 0.9)), 1)
        
        # Simulated predicted std decreases with better (higher) sensitivity when high variance
        pred_std = max(30.0, data["std_glucose"] * (1.0 - 0.25 * abs(factor - 1.0) * 4))
        
        output = {
            "isf": isf,
            "icr": icr,
            "predicted_std": round(pred_std, 1),
            "rationale": f"Factor {factor:.2f} from critique: {critique or 'initial'}"
        }
        self.history.append(output)
        return output

class Verifier:
    def verify(self, candidate: Dict, data: Dict) -> Tuple[bool, str]:
        pred_std = candidate["predicted_std"]
        isf = candidate["isf"]
        lo, hi = SUCCESS_CRITERION["isf_range"]
        
        fails = []
        passes = []
        
        if pred_std <= SUCCESS_CRITERION["max_predicted_std"]:
            passes.append(f"pred_std {pred_std} <= 40.0")
        else:
            fails.append(f"high variance: pred_std {pred_std} > 40.0")
        
        if lo <= isf <= hi:
            passes.append(f"ISF {isf} in [{lo},{hi}]")
        else:
            fails.append(f"ISF {isf} outside range")
        
        if data["hypo_events_week"] > 2.0 and isf > 70:
            fails.append("high hypo rate but ISF not reduced enough")
        
        success = len(fails) == 0
        reason = "; ".join(passes if success else fails)
        return success, reason

class Updater:
    def __init__(self, generator: Generator, verifier: Verifier):
        self.generator = generator
        self.verifier = verifier
        self.logs: List[Dict] = []
    
    def run_loop(self, data: Dict, max_passes: int = 3) -> List[Dict]:
        critique = ""
        for i in range(1, max_passes + 1):
            candidate = self.generator.generate(data, critique)
            success, reason = self.verifier.verify(candidate, data)
            log_entry = {
                "pass": i,
                "candidate": candidate,
                "success": success,
                "reason": reason,
                "critique_in": critique
            }
            self.logs.append(log_entry)
            if success:
                break
            critique = reason
        return self.logs

def main():
    gen = Generator()
    ver = Verifier()
    upd = Updater(gen, ver)
    
    logs = upd.run_loop(SAMPLE_DATA)
    
    print("=== Smoke Test Results ===")
    for log in logs:
        c = log["candidate"]
        print(f"Pass {log['pass']}: success={log['success']}, ISF={c['isf']}, ICR={c['icr']}, pred_std={c['predicted_std']}")
        print(f"  Reason: {log['reason']}")
    
    first = logs[0]["candidate"]
    last = logs[-1]["candidate"]
    print(f"\nBefore: ISF {first['isf']}, ICR {first['icr']}, std {first['predicted_std']}")
    print(f"After:  ISF {last['isf']}, ICR {last['icr']}, std {last['predicted_std']}")
    
    with open("smoke_test.json", "w") as f:
        json.dump({"sample": SAMPLE_DATA, "logs": logs}, f, indent=2)
    
    print("\nSmoke test logged to smoke_test.json")

if __name__ == "__main__":
    main()
