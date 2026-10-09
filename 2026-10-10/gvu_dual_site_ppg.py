"""Dual-site PPG concordance gate (GVU).

Prototypes the underexploited split in Ang et al. 2024 (Singapore Med J):
an 8-minute wrist PPG and an in-ear PPG were collected together, and
wearable features only beat demographics (AUC 0.75 -> 0.82) when the
signal was usable. This agent refuses a glucose-risk label when the two
sites disagree, and only emits elevated_glucose_risk when they agree
and the post-load index crosses the paper-inspired cutoff.

Not a medical device. Educational prototype only.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


POST_LOAD_CUTOFF = 0.62
MAX_SITE_DELTA = 0.15


@dataclass
class Candidate:
    label: str
    confidence: float
    features_used: list[str]
    rationale: str
    post_load_index: float
    site_delta: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _post_load_index(sample: dict[str, float]) -> float:
    wrist = 0.6 * sample["wrist_ac_dc"] + 0.4 * sample["wrist_pulse_amp"]
    ear = 0.6 * sample["ear_ac_dc"] + 0.4 * sample["ear_pulse_amp"]
    return round((wrist + ear) / 2, 4)


def _site_delta(sample: dict[str, float]) -> float:
    return round(abs(sample["wrist_ac_dc"] - sample["ear_ac_dc"]), 4)


def generate(sample: dict[str, Any], critique: str | None = None) -> Candidate:
    index = _post_load_index(sample)
    delta = _site_delta(sample)
    if critique is None:
        wrist_only = 0.6 * sample["wrist_ac_dc"] + 0.4 * sample["wrist_pulse_amp"]
        label = "normal" if wrist_only < 0.70 else "elevated_glucose_risk"
        return Candidate(
            label=label,
            confidence=0.71,
            features_used=["wrist_ac_dc", "wrist_pulse_amp", "age"],
            rationale="Wrist PPG alone looks modest; no ear check.",
            post_load_index=round(wrist_only, 4),
            site_delta=delta,
        )

    if delta > MAX_SITE_DELTA:
        return Candidate(
            label="insufficient_signal",
            confidence=0.9,
            features_used=["wrist_ac_dc", "ear_ac_dc", "site_delta"],
            rationale=(
                f"Sites disagree (delta {delta} > {MAX_SITE_DELTA}); "
                "refuse a glucose label and ask for a repeat 8-minute capture."
            ),
            post_load_index=index,
            site_delta=delta,
        )

    label = "elevated_glucose_risk" if index >= POST_LOAD_CUTOFF else "normal"
    return Candidate(
        label=label,
        confidence=0.84 if label == "elevated_glucose_risk" else 0.8,
        features_used=["wrist_ac_dc", "ear_ac_dc", "wrist_pulse_amp", "ear_pulse_amp", "age"],
        rationale=(
            f"Sites agree (delta {delta}). Dual-site post-load index {index} "
            f"{'meets' if index >= POST_LOAD_CUTOFF else 'is under'} cutoff {POST_LOAD_CUTOFF}."
        ),
        post_load_index=index,
        site_delta=delta,
    )


def verify(sample: dict[str, Any], candidate: Candidate) -> dict[str, Any]:
    reasons: list[str] = []
    delta = _site_delta(sample)
    index = _post_load_index(sample)

    uses_both = "wrist_ac_dc" in candidate.features_used and "ear_ac_dc" in candidate.features_used
    if not uses_both:
        reasons.append("features_used must include both wrist_ac_dc and ear_ac_dc")

    if delta > MAX_SITE_DELTA and candidate.label != "insufficient_signal":
        reasons.append(
            f"site_delta {delta} > {MAX_SITE_DELTA}; label must be insufficient_signal, not {candidate.label}"
        )

    if delta <= MAX_SITE_DELTA and index >= POST_LOAD_CUTOFF and candidate.label != "elevated_glucose_risk":
        reasons.append(
            f"sites agree and post_load_index {index} >= {POST_LOAD_CUTOFF}; "
            f"label must be elevated_glucose_risk, got {candidate.label}"
        )

    if delta <= MAX_SITE_DELTA and index < POST_LOAD_CUTOFF and candidate.label != "normal":
        reasons.append(
            f"sites agree and post_load_index {index} < {POST_LOAD_CUTOFF}; label must be normal"
        )

    if not 0.0 <= candidate.confidence <= 1.0:
        reasons.append("confidence out of range")

    return {"pass": not reasons, "reasons": reasons, "expected_index": index, "expected_delta": delta}


def update(sample: dict[str, Any], candidate: Candidate, verdict: dict[str, Any]) -> Candidate:
    critique = "; ".join(verdict["reasons"]) if verdict["reasons"] else "pass"
    return generate(sample, critique=critique)


def run(sample: dict[str, Any], passes: int = 3) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []
    candidate = generate(sample, None)
    for i in range(1, passes + 1):
        verdict = verify(sample, candidate)
        log.append({"pass": i, "candidate": candidate.to_dict(), "verdict": verdict})
        if verdict["pass"]:
            break
        candidate = update(sample, candidate, verdict)
    return log


SAMPLE = {
    "id": "P-1010",
    "age": 46,
    "wrist_ac_dc": 0.58,
    "ear_ac_dc": 0.71,
    "wrist_pulse_amp": 0.55,
    "ear_pulse_amp": 0.74,
}


if __name__ == "__main__":
    trace = run(SAMPLE)
    print(json.dumps({"sample": SAMPLE, "trace": trace}, indent=2))
