# GVU Self-Improving Agent: Smartphone PPG Diabetes Risk Score
# Based on Avram et al. (Nature Medicine) digital biomarker insight
# Date: 2026-11-15
# Opportunity: Multi-agent refinement of camera-based PPG risk scores

from dataclasses import dataclass
from typing import Dict, List, Tuple
import json

@dataclass
class PPGFeatures:
    age: int
    bmi: float
    heart_rate_variability: float  # lower = higher risk proxy
    pulse_wave_amplitude: float    # proxy for vascular stiffness
    known_prediabetes: bool

class Generator:
    def __init__(self):
        self.history = []
    
    def generate(self, features: PPGFeatures, critique: str = "") -> Dict:
        # Simple heuristic baseline, refined by critique
        base_score = 0.0
        if features.age > 45:
            base_score += 0.2
        if features.bmi > 30:
            base_score += 0.3
        if features.heart_rate_variability < 30:
            base_score += 0.25
        if features.pulse_wave_amplitude < 0.5:
            base_score += 0.15
        if features.known_prediabetes:
            base_score += 0.2
        
        # Clamp base before critique
        base_score = max(0.0, min(1.0, base_score))
        
        # Apply critique refinements
        if "overweight" in critique.lower() or "bmi" in critique.lower():
            base_score = min(1.0, base_score + 0.1)
        if "vascular" in critique.lower() or "stiffness" in critique.lower():
            base_score = min(1.0, base_score + 0.05)
        if "too high" in critique.lower():
            base_score = max(0.0, base_score - 0.1)
        
        # Always clamp
        base_score = max(0.0, min(1.0, base_score))
        
        risk_level = "high" if base_score > 0.6 else "moderate" if base_score > 0.35 else "low"
        
        output = {
            "risk_score": round(base_score, 3),
            "risk_level": risk_level,
            "rationale": f"Age {features.age}, BMI {features.bmi}, HRV {features.heart_rate_variability}, PWA {features.pulse_wave_amplitude}",
            "pass": 0
        }
        self.history.append(output)
        return output

class Verifier:
    def verify(self, output: Dict, features: PPGFeatures) -> Tuple[bool, str]:
        # Explicit success criteria:
        # 1. Score must be between 0 and 1
        # 2. If BMI > 30 and age > 45, score must be >= 0.5
        # 3. Risk level consistent with score
        score = output["risk_score"]
        level = output["risk_level"]
        
        reasons = []
        passed = True
        
        if not (0 <= score <= 1):
            passed = False
            reasons.append("Score out of [0,1]")
        
        if features.bmi > 30 and features.age > 45 and score < 0.5:
            passed = False
            reasons.append("High BMI + age should yield score >= 0.5")
        
        expected_level = "high" if score > 0.6 else "moderate" if score > 0.35 else "low"
        if level != expected_level:
            passed = False
            reasons.append(f"Risk level mismatch: got {level}, expected {expected_level}")
        
        critique = "; ".join(reasons) if reasons else "All criteria met"
        return passed, critique

class Updater:
    def __init__(self, generator: Generator, verifier: Verifier):
        self.generator = generator
        self.verifier = verifier
        self.logs = []
    
    def run_loop(self, features: PPGFeatures, max_passes: int = 3) -> List[Dict]:
        critique = ""
        results = []
        for pass_num in range(1, max_passes + 1):
            output = self.generator.generate(features, critique)
            passed, critique = self.verifier.verify(output, features)
            output["pass"] = pass_num
            output["verified"] = passed
            output["critique"] = critique
            results.append(output)
            self.logs.append(output)
            if passed:
                break
        return results

def smoke_test():
    features = PPGFeatures(
        age=52,
        bmi=32.5,
        heart_rate_variability=25.0,
        pulse_wave_amplitude=0.4,
        known_prediabetes=True
    )
    gen = Generator()
    ver = Verifier()
    upd = Updater(gen, ver)
    results = upd.run_loop(features)
    
    print("=== Smoke Test Results ===")
    for r in results:
        print(json.dumps(r, indent=2))
    return results

if __name__ == "__main__":
    smoke_test()
