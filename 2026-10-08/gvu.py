"""Day 2026-10-08 — composite-outcome DPP closer (GVU).

Prototypes the underexploited result in Mathioudakis et al., JAMA 2025
(AI-led DPP noninferior to human coaching): initiation was higher for AI,
but ~68% still missed the composite. The product seed is a missing-component
closer, not another generic coach.

Not a medical device. Educational prototype only.
"""

from __future__ import annotations

from dataclasses import dataclass

TARGETS = {
    "weight_loss_pct": 5.0,
    "activity_min_per_week": 150,
    "hba1c_drop": 0.2,
}


@dataclass
class Patient:
    patient_id: str
    baseline_weight_kg: float
    current_weight_kg: float
    activity_min_per_week: int
    baseline_hba1c: float
    current_hba1c: float
    barrier: str


def gaps(p: Patient) -> dict[str, float]:
    weight_loss = (p.baseline_weight_kg - p.current_weight_kg) / p.baseline_weight_kg * 100
    return {
        "weight_loss_pct": round(TARGETS["weight_loss_pct"] - weight_loss, 2),
        "activity_min_per_week": float(TARGETS["activity_min_per_week"] - p.activity_min_per_week),
        "hba1c_drop": round(TARGETS["hba1c_drop"] - (p.baseline_hba1c - p.current_hba1c), 2),
    }


def missing(p: Patient) -> list[str]:
    g = gaps(p)
    return [k for k, v in g.items() if v > 0]


def generate(p: Patient, critique: str | None = None) -> dict:
    """Generator. Pass 1 is the common failure mode: coach the already-met activity limb."""
    g = gaps(p)
    open_gaps = missing(p)
    if critique is None:
        return {
            "patient_id": p.patient_id,
            "component": "activity_min_per_week",
            "gap": g["activity_min_per_week"],
            "action": "Add a 20-minute evening walk three days this week.",
            "check_7d": "Log total walking minutes.",
            "pass_note": "generic activity nudge",
        }
    if not open_gaps:
        return {
            "patient_id": p.patient_id,
            "component": "none",
            "gap": 0.0,
            "action": "Hold current plan; composite already met.",
            "check_7d": "Recompute all three limbs in 7 days.",
            "pass_note": "maintenance",
        }
    component = max(open_gaps, key=lambda k: g[k])
    if component == "weight_loss_pct":
        action = (
            f"Replace the daily {p.barrier} with a 400 kcal plate "
            f"(protein + vegetables) on 5 of 7 days to close a "
            f"{g[component]:.2f} percentage-point weight-loss gap."
        )
        check = "Weigh on day 7; recompute percent loss from baseline."
    elif component == "hba1c_drop":
        action = (
            f"Cut the largest evening carb portion in half at dinner for 7 nights "
            f"to close a {g[component]:.2f} point HbA1c-drop gap (lab still required)."
        )
        check = "Day-7 fasting glucose mean versus this week's mean; schedule HbA1c if due."
    else:
        action = (
            f"Add {int(g[component])} minutes of brisk walking this week, "
            f"split across days after the {p.barrier} window."
        )
        check = "Day-7 activity minutes versus 150."
    return {
        "patient_id": p.patient_id,
        "component": component,
        "gap": g[component],
        "action": action,
        "check_7d": check,
        "pass_note": "critique-conditioned",
    }


def verify(p: Patient, draft: dict) -> dict:
    """PASS iff the draft targets a still-missing composite limb, states the computed gap,
    includes a numeric action, and names a day-7 check.
    """
    g = gaps(p)
    reasons: list[str] = []
    component = draft.get("component")
    if component not in TARGETS:
        reasons.append(f"component {component!r} is not a composite limb")
    else:
        if g[component] <= 0:
            reasons.append(f"{component} already met (gap {g[component]})")
        stated = float(draft.get("gap", 999))
        if abs(stated - g[component]) > 0.05:
            reasons.append(f"gap {stated} != computed {g[component]}")
    action = str(draft.get("action", ""))
    if not any(ch.isdigit() for ch in action):
        reasons.append("action has no numeric dose")
    check = str(draft.get("check_7d", "")).lower()
    if "7" not in check:
        reasons.append("check_7d missing a 7-day metric")
    ok = not reasons
    return {"pass": ok, "reasons": reasons or ["ok"], "computed_gaps": g}
