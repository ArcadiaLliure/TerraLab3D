"""Projecció explícita aire/buit del polinomi espectral retingut; zero transport."""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass

import numpy as np

from terralab3d.domain.light_pollution.spectral_transport import SpectralRaySamples
from terralab3d.domain.photometric_projection import (
    AB_FNU_W_M2_HZ,
    ARCSEC2_SR,
    SPEED_OF_LIGHT_NM_S,
    BandSignal,
    ProjectionUnavailable,
    _validated_arrays,
)
from terralab3d.domain.wavelength_coordinates import CoordinateCurve


@dataclass(frozen=True, slots=True)
class CoordinateProjection:
    signal: BandSignal
    refinement_error: float
    input_radiance_basis: str
    response_basis: str
    scope: str = "Polinomi retingut declarat en buit; no transforma la SPD original ni acredita el sensor complet"
    physical_transport_evaluations: int = 0


def integrate_response(
    response: CoordinateCurve, function, bounds: tuple[float, float], *, order: int
) -> float:
    return _integrate_response_prepared(
        response, function, bounds, order=order, response_knots=response.vacuum_knots
    )


def _integrate_response_prepared(
    response: CoordinateCurve,
    function,
    bounds: tuple[float, float],
    *,
    order: int,
    response_knots: tuple[float, ...],
) -> float:
    if response.role != "response" or type(order) is not int or not 2 <= order <= 64:
        raise ValueError("Cal resposta i ordre de quadratura vàlids")
    lo, hi = bounds
    if not math.isfinite(lo) or not math.isfinite(hi) or lo >= hi:
        raise ValueError("Domini de projecció invàlid")
    a, b = response_knots[0], response_knots[-1]
    if response.curve.outside_support == "unavailable" and (lo < a or hi > b):
        raise ProjectionUnavailable(
            "Cua espectral desconeguda; cap extrapolació nul·la"
        )
    knots = sorted({lo, hi} | {w for w in response_knots if lo < w < hi})
    nodes, weights = np.polynomial.legendre.leggauss(order)
    terms = []
    for left, right in zip(knots, knots[1:]):
        middle, half = (left + right) / 2, (right - left) / 2
        for n, q in zip(nodes, weights, strict=True):
            w = middle + half * float(n)
            terms.append(half * float(q) * response.at_vacuum(w) * function(w))
    return math.fsum(terms)


def project_coordinate_band(
    samples: SpectralRaySamples,
    response: CoordinateCurve,
    *,
    input_radiance_basis: str,
    domain_nm: tuple[float, float],
    orders: tuple[int, int] = (8, 16),
) -> CoordinateProjection:
    if input_radiance_basis != "vacuum_nm":
        raise ProjectionUnavailable(
            "Cal identificar radiància per nm de buit; no s’infereix del fitxer antic"
        )
    x, y, errors, unit = _validated_arrays(samples)
    lo, hi = domain_nm
    if not x[0] <= lo < hi <= x[-1]:
        raise ProjectionUnavailable(
            "La retenció no cobreix el domini; no s’amplia el transport"
        )
    if len(orders) != 2 or orders[0] >= orders[1]:
        raise ValueError("Calen dos ordres creixents per al control de refinament")
    # Comprova tot el polinomi, no només els nusos: zeros i salts no es suavitzen.
    coefficients = []
    for left, middle, right in y:
        a = 2 * (right + left - 2 * middle)
        b = 4 * middle - 3 * left - right
        minimum = min(left, right)
        if a > 0 and 0 < -b / (2 * a) < 1:
            t = -b / (2 * a)
            minimum = min(minimum, left + b * t + a * t * t)
        if minimum < 0:
            raise ProjectionUnavailable(
                "Polinomi retingut negatiu entre nusos: no hi ha garantia física"
            )
        coefficients.append((float(left), float(b), float(a)))

    def density(w: float) -> float:
        i = min(bisect_right(x, w) - 1, len(x) - 2)
        t = (w - x[i]) / (x[i + 1] - x[i])
        c, b, a = coefficients[i]
        return float(c + b * t + a * t * t)

    # Parteix també als nusos retinguts: cap interpolació a través de panells/salts.
    breaks = sorted({lo, hi} | {float(w) for w in x if lo < w < hi})
    response_knots = response.vacuum_knots

    def value(order: int) -> float:
        return math.fsum(
            _integrate_response_prepared(
                response, density, (a, b), order=order, response_knots=response_knots
            )
            for a, b in zip(breaks, breaks[1:])
        )

    coarse, fine = (value(order) for order in orders)
    los_error = 0.0
    for a, b in zip(breaks, breaks[1:]):
        i = min(bisect_right(x, (a + b) / 2) - 1, len(x) - 2)
        los_error += float(max(errors[i])) * _integrate_response_prepared(
            response,
            lambda _: 1.0,
            (a, b),
            order=orders[1],
            response_knots=response_knots,
        )
    signal = BandSignal(
        fine,
        los_error,
        unit,
        samples.scale_id,
        f"{response.curve.source_id}:{response.basis}:coordinate-v2",
        (lo, hi),
        samples.band_set_id,
        samples.source_id,
        samples.direction_id,
    )
    return CoordinateProjection(
        signal, abs(fine - coarse), input_radiance_basis, response.basis
    )


def coordinate_ab_reference(response: CoordinateCurve, *, order: int = 16) -> float:
    """Referència AB en buit; el jacobià no multiplica T(λ), només la densitat."""
    return integrate_response(
        response,
        lambda w: AB_FNU_W_M2_HZ * SPEED_OF_LIGHT_NM_S / (ARCSEC2_SR * w * w),
        (response.vacuum_knots[0], response.vacuum_knots[-1]),
        order=order,
    )
