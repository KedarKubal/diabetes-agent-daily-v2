"""Smoke test: Generator–Verifier–Updater on one sample."""

from __future__ import annotations

import json
from pathlib import Path

from gvu import Patient, generate, verify

SAMPLE = Patient(
    patient_id="P-908",
    baseline_weight_kg=92.0,
    current_weight_kg=90.5,
    activity_min_per_week=160,
    baseline_hba1c=6.1,
    current_hba1c=6.05,
    barrier="afternoon soda",
)


def run() -> list[dict]:
    log: list[dict] = []
    critique: str | None = None
    for i in range(1, 4):
        draft = generate(SAMPLE, critique)
        verdict = verify(SAMPLE, draft)
        log.append({"pass_n": i, "draft": draft, "verdict": verdict})
        if verdict["pass"]:
            break
        critique = "; ".join(verdict["reasons"])
    Path(__file__).with_name("smoke_log.json").write_text(json.dumps(log, indent=2))
    return log


if __name__ == "__main__":
    for row in run():
        print(json.dumps(row, indent=2))
