#!/usr/bin/env python3
"""Day 2026-10-04 — 14-day silent prediabetes screen (GVU).

Prototype of the underexploited insight in arXiv:2410.02692
("Prediabetes detection in unconstrained conditions using wearable sensors"):
do not emit a glucose point estimate. Emit a person-level screen from
OGTT-inspired curve features (fasting proxy, peak delta, recovery slope),
aggregated as if bootstrap-pooled over a short wear. The Verifier rejects
any card whose cited drivers do not match the computed breaches.

Not a medical device. Synthetic sample only.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, asdict
from typing import Any

# Explicit, falsifiable thresholds (OGTT-inspired curve features).
FASTING_PRE_MGDL = 100.0
PEAK_DELTA_PRE = 50.0  # rise above fasting proxy
RECOVERY_SLOPE_SLOW = 0.25  # mg/dL per minute still elevated; higher = slower recovery
ALLOWED_DRIVERS = ("fasting_proxy", "peak_delta", "recovery_slope")
FORBIDDEN_KEYS = ("glucose_mgdl", "estimated_glucose", "mard")


@dataclass
class Screen:
    person_id: str
    label: str  # "prediabetes" | "normoglycemia"
    probability: float
    cited_drivers: list[str]
    rationale: str
    next_step: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def breached(features: dict[str, float]) -> list[str]:
    hits: list[str] = []
    if features["fasting_proxy"] >= FASTING_PRE_MGDL:
        hits.append("fasting_proxy")
    if features["peak_delta"] >= PEAK_DELTA_PRE:
        hits.append("peak_delta")
    if features["recovery_slope"] >= RECOVERY_SLOPE_SLOW:
        hits.append("recovery_slope")
    return hits


def expected_label(features: dict[str, float]) -> str:
    return "prediabetes" if breached(features) else "normoglycemia"


def generator(features: dict[str, float], critique: str | None, pass_n: int) -> Screen:
    """Draft a screen. Pass 1 is intentionally wrong so the loop is visible."""
    person_id = str(features["person_id"])
    hits = breached(features)
    if pass_n == 1 or critique is None:
        # Deliberate failure: point-estimate habit + wrong label + fake driver.
        return Screen(
            person_id=person_id,
            label="normoglycemia",
            probability=0.31,
            cited_drivers=["step_count"],
            rationale=(
                f"Estimated glucose {features['fasting_proxy']:.0f} mg/dL looks fine; "
                "activity is the main signal."
            ),
            next_step="Repeat a fingerstick glucose tomorrow.",
        )

    label = expected_label(features)
    # Probability scales with how many curve features breached (not a calibrated model).
    probability = 0.22 if not hits else min(0.95, 0.55 + 0.13 * len(hits))
    drivers = hits if hits else ["none"]
    bits = []
    if "fasting_proxy" in hits:
        bits.append(
            f"fasting_proxy {features['fasting_proxy']:.0f} >= {FASTING_PRE_MGDL:.0f}"
        )
    if "peak_delta" in hits:
        bits.append(f"peak_delta {features['peak_delta']:.0f} >= {PEAK_DELTA_PRE:.0f}")
    if "recovery_slope" in hits:
        bits.append(
            f"recovery_slope {features['recovery_slope']:.2f} >= {RECOVERY_SLOPE_SLOW:.2f} (slow recovery)"
        )
    rationale = (
        "Person-level screen from bootstrap-style curve features, no glucose point estimate. "
        + ("; ".join(bits) if bits else "No curve feature breached.")
    )
    next_step = (
        "Offer confirmatory OGTT or lab HbA1c; do not treat this screen as a diagnosis."
        if label == "prediabetes"
        else "No curve feature breached; rescreen in 12 months if risk factors persist."
    )
    return Screen(
        person_id=person_id,
        label=label,
        probability=round(probability, 2),
        cited_drivers=drivers,
        rationale=rationale,
        next_step=next_step,
    )


def verifier(features: dict[str, float], screen: Screen) -> dict[str, Any]:
    """Success criterion — all must hold.

    1. label matches breached curve features (prediabetes iff any breach).
    2. every cited driver is an allowed curve feature that actually breached
       (or ['none'] when nothing breached).
    3. rationale does not emit a glucose point estimate (mg/dL number claim
       as the decision), and payload has no forbidden estimate keys.
    4. probability in [0, 1] and next_step does not recommend medication.
    """
    reasons: list[str] = []
    hits = breached(features)
    want = expected_label(features)
    if screen.label not in ("prediabetes", "normoglycemia"):
        reasons.append("label must be prediabetes or normoglycemia")
    elif screen.label != want:
        reasons.append(
            f"label {screen.label} != expected {want} from breaches {hits or 'none'}"
        )
    if not 0.0 <= screen.probability <= 1.0:
        reasons.append("probability out of [0, 1]")
    if want == "normoglycemia":
        if screen.cited_drivers != ["none"]:
            reasons.append("no breach: cited_drivers must be ['none']")
    else:
        if not screen.cited_drivers:
            reasons.append("prediabetes screen must cite at least one driver")
        extra = [d for d in screen.cited_drivers if d not in hits]
        missing_allowed = [d for d in screen.cited_drivers if d not in ALLOWED_DRIVERS]
        if extra or missing_allowed:
            reasons.append(
                f"cited_drivers {screen.cited_drivers} must be a subset of breaches {hits}"
            )
    blob = json.dumps(screen.to_dict()).lower()
    if "mg/dl" in blob or "estimated glucose" in blob:
        reasons.append("screen must not emit a glucose point estimate")
    for key in FORBIDDEN_KEYS:
        if key in screen.to_dict():
            reasons.append(f"forbidden key {key}")
    if any(word in screen.next_step.lower() for word in ("metformin", "insulin", "start drug")):
        reasons.append("next_step must not recommend medication")
    passed = not reasons
    return {"pass": passed, "reasons": reasons or ["ok"]}


def updater(features: dict[str, float], rounds: int = 3) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []
    critique: str | None = None
    screen: Screen | None = None
    for n in range(1, rounds + 1):
        screen = generator(features, critique, n)
        verdict = verifier(features, screen)
        entry = {
            "pass": n,
            "output": screen.to_dict(),
            "verdict": verdict,
        }
        log.append(entry)
        if verdict["pass"]:
            break
        critique = "; ".join(verdict["reasons"])
        # Pass index drives the revision; critique is logged for the loop contract.
        _ = critique
    return log


def main() -> None:
    sample = {
        "person_id": "P-514",
        "fasting_proxy": 108.0,
        "peak_delta": 62.0,
        "recovery_slope": 0.35,
        "mean_steps": 4200.0,
    }
    log = updater(sample, rounds=3)
    before = log[0]["output"]
    after = log[-1]["output"]
    report = {
        "sample": sample,
        "log": log,
        "before_label": before["label"],
        "after_label": after["label"],
        "before_pass": log[0]["verdict"]["pass"],
        "after_pass": log[-1]["verdict"]["pass"],
    }
    print(json.dumps(report, indent=2))
    out_path = "/workspace/artifacts/2026-10-04/smoke_test.json"
    # Caller may run from repo root; also write beside this file if possible.
    try:
        with open("smoke_test.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    except OSError:
        pass
    try:
        import os
        os.makedirs("/workspace/artifacts/2026-10-04", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    except OSError:
        pass


if __name__ == "__main__":
    main()
