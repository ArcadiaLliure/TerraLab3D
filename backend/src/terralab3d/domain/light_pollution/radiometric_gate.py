"""Decisió numèrica prospectiva; cap factor de calibratge ni homologació C/H."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class GateDecision:
    status: str
    candidate: float
    reference: float
    reference_uncertainty: float
    absolute_error: float
    guarded_relative_error: float | None
    reason: str


def assess_transport(
    candidate: float,
    references: tuple[float, ...],
    los_errors: tuple[float, ...],
    *,
    relative_limit: float,
    reference_resolution: float,
) -> GateDecision:
    """Calen tres refinaments. La incertesa de l'oracle resta del marge admès.

    L'estimació no és aritmètica d'intervals; el seu origen es conserva al
    protocol. El cas fosc no introdueix una escala absoluta artificial.
    """
    if (
        len(references) != 3
        or len(los_errors) != 3
        or any(
            not math.isfinite(v) or v < 0 for v in (candidate, *references, *los_errors)
        )
    ):
        raise ValueError("Gate sense tres referències finites no negatives")
    if not (0 < reference_resolution < relative_limit < 1):
        raise ValueError("Jerarquia de precisió del gate invàlida")
    reference = references[-1]
    uncertainty = math.fsum(
        (
            abs(references[2] - references[1]),
            abs(references[1] - references[0]),
            *los_errors,
            64 * math.ulp(max(references)),
        )
    )
    # math.ulp(0) és subnormal, no una incertesa afegida a un zero exacte.
    if all(v == 0 for v in (*references, *los_errors)):
        uncertainty = 0.0
    error = abs(candidate - reference)
    if reference == 0:
        return GateDecision(
            "PASS" if candidate == 0 and uncertainty == 0 else "FAIL",
            candidate,
            reference,
            uncertainty,
            error,
            None,
            "cas fosc geomètric; zero exacte obligatori",
        )
    if uncertainty > reference_resolution * reference:
        return GateDecision(
            "REFERENCE_UNRESOLVED",
            candidate,
            reference,
            uncertainty,
            error,
            None,
            "SG-REF no acredita la resolució preregistrada",
        )
    if reference <= uncertainty / relative_limit:
        return GateDecision(
            "PASS" if error <= uncertainty else "FAIL",
            candidate,
            reference,
            uncertainty,
            error,
            None,
            "senyal no resolt respecte del pressupost; mètrica absoluta",
        )
    guarded = (error + uncertainty) / reference
    return GateDecision(
        "PASS" if guarded <= relative_limit else "FAIL",
        candidate,
        reference,
        uncertainty,
        error,
        guarded,
        "error del candidat més incertesa estimada de SG-REF",
    )
