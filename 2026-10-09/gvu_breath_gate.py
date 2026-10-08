"""Breath-acetone selectivity gate — GVU prototype (2026-10-09).

Core insight from Swargiary et al., Biosensors and Bioelectronics 271 (2025) 117061:
the ZnO no-core fiber reports acetone sensitivity 0.116 nm/ppm and 0.2% drift,
but LOD is 3.26 ppm — above the clinical breath window (~0.2–2.5 ppm).
The underexploited move is multi-breath stacking plus interferent subtraction
using the six-VOC panel already in the paper, not another coating.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


PAPER_SENSITIVITY_NM_PER_PPM = 0.116
PAPER_SINGLE_SHOT_LOD_PPM = 3.26
PAPER_DRIFT_30D_PCT = 0.2
CLINICAL_SCREEN_PPM = 1.8
MIN_SELECTIVITY = 3.0
MAX_DRIFT_PCT = 0.5
TARGET_LOD_PPM = 1.5


@dataclass
class BreathSample:
    sample_id: str
    wavelength_shift_nm: float
    ethanol_shift_nm: float
    isopropanol_shift_nm: float
    n_breaths: int
    drift_30d_pct: float


@dataclass
class ScreenDraft:
    sample_id: str
    raw_acetone_ppm: float
    corrected_acetone_ppm: float
    effective_lod_ppm: float
    selectivity_vs_ethanol: float
    drift_30d_pct: float
    label: str
    rationale: str
    passes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _raw_ppm(shift_nm: float) -> float:
    if PAPER_SENSITIVITY_NM_PER_PPM <= 0:
        raise ValueError("sensitivity must be positive")
    return round(shift_nm / PAPER_SENSITIVITY_NM_PER_PPM, 3)


class Generator:
    def generate(self, sample: BreathSample, critique: str | None = None) -> ScreenDraft:
        raw = _raw_ppm(sample.wavelength_shift_nm)
        ethanol_ppm_eq = _raw_ppm(sample.ethanol_shift_nm)
        selectivity = round(raw / ethanol_ppm_eq, 3) if ethanol_ppm_eq else 99.0

        if critique is None:
            label = "diabetes_screen" if raw >= CLINICAL_SCREEN_PPM else "norm_breath"
            return ScreenDraft(
                sample_id=sample.sample_id,
                raw_acetone_ppm=raw,
                corrected_acetone_ppm=raw,
                effective_lod_ppm=PAPER_SINGLE_SHOT_LOD_PPM,
                selectivity_vs_ethanol=selectivity,
                drift_30d_pct=sample.drift_30d_pct,
                label=label,
                rationale="single-shot ZnO shift / 0.116 nm/ppm; paper LOD left unchanged",
            )

        n = max(sample.n_breaths, 1)
        effective_lod = round(PAPER_SINGLE_SHOT_LOD_PPM / (n ** 0.5), 3)
        interferent = 0.35 * ethanol_ppm_eq + 0.15 * _raw_ppm(sample.isopropanol_shift_nm)
        corrected = round(max(raw - interferent, 0.0), 3)
        if effective_lod > TARGET_LOD_PPM or selectivity < MIN_SELECTIVITY or sample.drift_30d_pct > MAX_DRIFT_PCT:
            label = "reject_reading"
            why = "effective LOD, selectivity, or drift outside gate"
        elif corrected >= CLINICAL_SCREEN_PPM and corrected >= effective_lod:
            label = "prediabetes_screen"
            why = "corrected acetone above 1.8 ppm and above stacked LOD"
        else:
            label = "insufficient_for_screen"
            why = "corrected acetone inside healthy/overlap band"
        return ScreenDraft(
            sample_id=sample.sample_id,
            raw_acetone_ppm=raw,
            corrected_acetone_ppm=corrected,
            effective_lod_ppm=effective_lod,
            selectivity_vs_ethanol=selectivity,
            drift_30d_pct=sample.drift_30d_pct,
            label=label,
            rationale=why + f" | critique: {critique}",
        )


class Verifier:
    def check(self, draft: ScreenDraft) -> dict[str, Any]:
        reasons: list[str] = []
        if draft.effective_lod_ppm > TARGET_LOD_PPM:
            reasons.append(
                f"effective_lod_ppm {draft.effective_lod_ppm} > {TARGET_LOD_PPM} "
                "(single-shot 3.26 ppm cannot resolve 0.2-2.5 ppm window)"
            )
        if draft.selectivity_vs_ethanol < MIN_SELECTIVITY:
            reasons.append(
                f"selectivity_vs_ethanol {draft.selectivity_vs_ethanol} < {MIN_SELECTIVITY}"
            )
        if draft.drift_30d_pct > MAX_DRIFT_PCT:
            reasons.append(f"drift_30d_pct {draft.drift_30d_pct} > {MAX_DRIFT_PCT}")
        if draft.label in {"diabetes_screen", "prediabetes_screen"} and draft.corrected_acetone_ppm < draft.effective_lod_ppm:
            reasons.append("screen label issued below effective LOD")
        if draft.label == "diabetes_screen":
            reasons.append("label must be prediabetes_screen or reject/insufficient, never a diagnosis")
        if draft.label in {"diabetes_screen", "prediabetes_screen"} and draft.corrected_acetone_ppm < CLINICAL_SCREEN_PPM:
            reasons.append("screen label below 1.8 ppm corrected acetone")
        passed = not reasons
        return {"pass": passed, "reasons": reasons or ["all gates held"]}


class Updater:
    def __init__(self, rounds: int = 3) -> None:
        self.generator = Generator()
        self.verifier = Verifier()
        self.rounds = rounds

    def run(self, sample: BreathSample) -> dict[str, Any]:
        log: list[dict[str, Any]] = []
        critique: str | None = None
        draft = self.generator.generate(sample, critique)
        for i in range(1, self.rounds + 1):
            verdict = self.verifier.check(draft)
            log.append({"pass": i, "draft": draft.to_dict(), "verdict": verdict})
            if verdict["pass"]:
                break
            critique = "; ".join(verdict["reasons"])
            draft = self.generator.generate(sample, critique)
        return {"sample_id": sample.sample_id, "log": log, "final": draft.to_dict()}


SAMPLE = BreathSample(
    sample_id="BR-1009",
    wavelength_shift_nm=0.348,
    ethanol_shift_nm=0.058,
    isopropanol_shift_nm=0.023,
    n_breaths=9,
    drift_30d_pct=0.2,
)


def main() -> None:
    result = Updater(rounds=3).run(SAMPLE)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
