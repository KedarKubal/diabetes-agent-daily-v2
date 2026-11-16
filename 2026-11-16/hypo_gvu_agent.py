#!/usr/bin/env python3
"""
Minimal self-improving multi-agent prototype for week-ahead hypoglycemia risk flagging.
Based on CGM feature insights (low glucose index, TBR, CV, etc.).
Generator-Verifier-Updater (GVU) pattern from CS329A.
Smoke-test on one sample CGM week summary.
"""

import json
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class CGMSummary:
    mean_glucose: float
    tbr_pct: float  # time below range %
    cv: float       # coefficient of variation %
    low_glucose_index: float
    night_hypo_events: int

class Generator:
    def __init__(self):
        self.version = 1

    def generate(self, summary: CGMSummary, critique: str = "") -> Dict[str, Any]:
        # Simple heuristic baseline, refined by critique
        risk_score = 0.0
        reasons = []

        if summary.tbr_pct > 4.0:
            risk_score += 0.15
            reasons.append(f"High TBR {summary.tbr_pct:.1f}%")
        if summary.cv > 36.0:
            risk_score += 0.10
            reasons.append(f"High CV {summary.cv:.1f}%")
        if summary.low_glucose_index > 1.5:
            risk_score += 0.05
            reasons.append(f"Elevated LGI {summary.low_glucose_index:.2f}")
        if summary.night_hypo_events > 2:
            risk_score += 0.05
            reasons.append(f"{summary.night_hypo_events} nocturnal hypos")

        # Incorporate critique if present
        if "underestimated" in critique.lower() or "increase" in critique.lower():
            risk_score = min(1.0, risk_score + 0.15)
            reasons.append("Adjusted upward per verifier critique")

        risk_level = "HIGH" if risk_score >= 0.5 else "MODERATE" if risk_score >= 0.3 else "LOW"
        return {
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "reasons": reasons,
            "version": self.version,
            "critique_applied": bool(critique)
        }

class Verifier:
    SUCCESS_CRITERION = (
        "Pass if: (1) risk_score is between 0 and 1, (2) if TBR>4 and CV>36 then risk_level must be at least MODERATE, "
        "(3) reasons list is non-empty when score > 0.2, (4) no contradiction with input features."
    )

    def verify(self, summary: CGMSummary, candidate: Dict[str, Any]) -> Dict[str, Any]:
        passed = True
        reasons = []

        score = candidate.get("risk_score", -1)
        if not (0 <= score <= 1):
            passed = False
            reasons.append("risk_score out of [0,1]")

        if summary.tbr_pct > 4.0 and summary.cv > 36.0:
            if candidate.get("risk_level") == "LOW":
                passed = False
                reasons.append("High TBR+CV but flagged LOW — underestimated risk")

        if score > 0.2 and not candidate.get("reasons"):
            passed = False
            reasons.append("Score elevated but no reasons given")

        # Simple consistency
        if summary.tbr_pct < 2.0 and score > 0.6:
            passed = False
            reasons.append("Low TBR but high score — overestimated")

        return {
            "pass": passed,
            "critique": "; ".join(reasons) if reasons else "Meets all success criteria.",
            "criterion": self.SUCCESS_CRITERION
        }

class Updater:
    def __init__(self, generator: Generator, verifier: Verifier):
        self.generator = generator
        self.verifier = verifier
        self.logs: List[Dict] = []

    def run_loop(self, summary: CGMSummary, max_passes: int = 3) -> List[Dict]:
        critique = ""
        for i in range(1, max_passes + 1):
            candidate = self.generator.generate(summary, critique)
            verification = self.verifier.verify(summary, candidate)
            entry = {
                "pass": i,
                "candidate": candidate,
                "verification": verification
            }
            self.logs.append(entry)
            if verification["pass"]:
                break
            critique = verification["critique"]
            self.generator.version += 1
        return self.logs

def main():
    # Sample: patient with elevated risk features (from typical CGM literature)
    sample = CGMSummary(
        mean_glucose=140.0,
        tbr_pct=6.5,
        cv=42.0,
        low_glucose_index=2.1,
        night_hypo_events=3
    )

    gen = Generator()
    ver = Verifier()
    updater = Updater(gen, ver)

    print("=== Smoke Test: Week-Ahead Hypoglycemia Risk Flagging ===\n")
    print(f"Input CGM summary: {sample}\n")

    logs = updater.run_loop(sample, max_passes=3)

    for entry in logs:
        print(f"--- Pass {entry['pass']} ---")
        print(json.dumps(entry["candidate"], indent=2))
        print(f"Verifier: {'PASS' if entry['verification']['pass'] else 'FAIL'}")
        print(f"Critique: {entry['verification']['critique']}\n")

    final = logs[-1]["candidate"]
    print(f"Final output after {len(logs)} pass(es): risk_level={final['risk_level']}, score={final['risk_score']}")

if __name__ == "__main__":
    main()
