#!/usr/bin/env python3
"""
Minimal GVU prototype for phenotype-routed digital lifestyle intervention
to delay diabetes onset / improve glycemic control.
Based on insight: different pathophysiological/genetic subgroups respond
differently to lifestyle doses (activity vs diet restraint).
"""

from dataclasses import dataclass
from typing import Dict, Any
import json

@dataclass
class Patient:
    id: str
    bmi: float
    insulin_resistance: bool
    fto_risk: bool
    current_hba1c: float
    current_activity_min: int  # daily moderate activity
    diet_restraint_score: int  # 1-10

def generator(patient: Patient, critique: str = "") -> Dict[str, Any]:
    """Generate a candidate lifestyle intervention plan."""
    # Start conservative; critique forces stronger phenotype routing
    if not critique:
        activity = patient.current_activity_min + 5
        restraint = patient.diet_restraint_score + 1
    elif "insufficient activity" in critique.lower() or patient.bmi > 30:
        activity = max(40, patient.current_activity_min + 20)
        restraint = max(6, patient.diet_restraint_score)
    elif patient.fto_risk:
        activity = patient.current_activity_min + 10
        restraint = min(9, patient.diet_restraint_score + 3)
    else:
        activity = patient.current_activity_min + 15
        restraint = patient.diet_restraint_score + 2

    # Incorporate critique for low drop
    if "low predicted drop" in critique.lower() or (not critique and True):
        if critique:
            activity += 10
            restraint += 1

    predicted_drop = (activity - patient.current_activity_min) * 0.015 + (restraint - patient.diet_restraint_score) * 0.08
    if patient.insulin_resistance and critique:
        predicted_drop *= 1.2

    return {
        "patient_id": patient.id,
        "activity_min_day": activity,
        "diet_restraint": restraint,
        "predicted_hba1c_drop": round(predicted_drop, 2),
        "rationale": f"Phenotype-routed: BMI={patient.bmi}, IR={patient.insulin_resistance}, FTO={patient.fto_risk}" + (f" | updated by critique" if critique else " | initial")
    }

def verifier(output: Dict[str, Any], patient: Patient) -> Dict[str, Any]:
    """Explicit success criterion: predicted HbA1c drop >= 0.3 AND activity increase >=15 min AND restraint increase >=2."""
    drop = output["predicted_hba1c_drop"]
    act_inc = output["activity_min_day"] - patient.current_activity_min
    rest_inc = output["diet_restraint"] - patient.diet_restraint_score

    passes = drop >= 0.3 and act_inc >= 15 and rest_inc >= 2
    reason = (
        f"drop={drop} (>=0.3), act_inc={act_inc} (>=15), rest_inc={rest_inc} (>=2). "
        f"{'PASS' if passes else 'FAIL'}"
    )
    return {"pass": passes, "reason": reason, "critique": reason if not passes else ""}

def updater_loop(patient: Patient, max_passes: int = 3) -> list:
    """Run Generator-Verifier-Updater loop, log each pass."""
    logs = []
    critique = ""
    for i in range(1, max_passes + 1):
        candidate = generator(patient, critique)
        verdict = verifier(candidate, patient)
        logs.append({
            "pass": i,
            "output": candidate,
            "verdict": verdict
        })
        if verdict["pass"]:
            break
        critique = verdict["critique"]
    return logs

if __name__ == "__main__":
    # Smoke test sample
    sample = Patient(
        id="P-1810",
        bmi=32.5,
        insulin_resistance=True,
        fto_risk=True,
        current_hba1c=6.4,
        current_activity_min=10,
        diet_restraint_score=3
    )
    results = updater_loop(sample)
    print(json.dumps(results, indent=2))
    with open("smoke_test.json", "w") as f:
        json.dump(results, f, indent=2)
