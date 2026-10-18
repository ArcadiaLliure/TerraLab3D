"""Oracle espectral fi independent del model DNB i del futur kernel.

La quadratura de Gauss-Legendre es parteix a cada nus de les taules d'entrada.
Les corbes CIE declaren interpolació lineal i extrapolació nul·la; l'oracle
preserva aquestes convencions sense seleccionar cap SpectralBandSet candidat.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np


SPECTRAL_RADIANCE_UNIT = "nW cm^-2 sr^-1 nm^-1"
RADIANCE_UNIT = "nW cm^-2 sr^-1"
RELATIVE_UNIT = "relative"
DIMENSIONLESS_UNIT = "dimensionless"


@dataclass(frozen=True, slots=True)
class SpectralCurve:
    source_id: str
    wavelengths_nm: tuple[float, ...]
    values: tuple[float, ...]
    unit: str
    outside_support: Literal["zero", "unavailable"] = "unavailable"

    def __post_init__(self) -> None:
        if not self.source_id:
            raise ValueError("Cal la procedència de la corba")
        if len(self.wavelengths_nm) < 2 or len(self.wavelengths_nm) != len(self.values):
            raise ValueError("La corba requereix almenys dos nusos i valors aparellats")
        if any(not math.isfinite(x) for x in (*self.wavelengths_nm, *self.values)):
            raise ValueError("La corba conté valors no finits")
        if any(b <= a for a, b in zip(self.wavelengths_nm, self.wavelengths_nm[1:])):
            raise ValueError("Les longituds d'ona han de ser estrictament creixents")
        if self.unit not in {SPECTRAL_RADIANCE_UNIT, RELATIVE_UNIT, DIMENSIONLESS_UNIT}:
            raise ValueError("Unitat espectral desconeguda")
        if self.outside_support not in {"zero", "unavailable"}:
            raise ValueError("Política de suport espectral desconeguda")
        if self.unit in {SPECTRAL_RADIANCE_UNIT, RELATIVE_UNIT} and any(value < 0 for value in self.values):
            raise ValueError("La font espectral no pot tenir valors negatius")


@dataclass(frozen=True, slots=True)
class SpectralOracleResult:
    value: float
    unit: str
    wavelength_start_nm: float
    wavelength_end_nm: float
    quadrature_order: int
    interval_count: int
    source_ids: tuple[str, ...]


def integrate_spectral_product(
    source: SpectralCurve,
    responses: tuple[SpectralCurve, ...],
    wavelength_start_nm: float,
    wavelength_end_nm: float,
    *,
    quadrature_order: int = 8,
) -> SpectralOracleResult:
    """Integra font i respostes amb nusos conjunts, sense normalitzar cap RSR.

    El resultat és una integral de radiància o d'una forma SPD relativa. Una
    corba de resposta pot ser CIE, un sensor o una transmissió tabulada;
    cap identificador de font implica que estigui homologada per a producte.
    """

    if source.unit not in {SPECTRAL_RADIANCE_UNIT, RELATIVE_UNIT}:
        raise ValueError("La font ha de ser radiància espectral o SPD relativa")
    if not responses or any(curve.unit != DIMENSIONLESS_UNIT for curve in responses):
        raise ValueError("Cal almenys una resposta adimensional")
    if not (
        math.isfinite(wavelength_start_nm)
        and math.isfinite(wavelength_end_nm)
        and wavelength_start_nm < wavelength_end_nm
    ):
        raise ValueError("Domini espectral invàlid")
    if quadrature_order < 2:
        raise ValueError("L'ordre de quadratura ha de ser almenys dos")

    curves = (source, *responses)
    for curve in curves:
        if curve.outside_support == "unavailable" and (
            wavelength_start_nm < curve.wavelengths_nm[0]
            or wavelength_end_nm > curve.wavelengths_nm[-1]
        ):
            raise ValueError(f"El domini supera el suport de {curve.source_id}")
    knots = sorted({wavelength_start_nm, wavelength_end_nm} | {
        wavelength
        for curve in curves
        for wavelength in curve.wavelengths_nm
        if wavelength_start_nm < wavelength < wavelength_end_nm
    })
    nodes, weights = np.polynomial.legendre.leggauss(quadrature_order)
    terms: list[float] = []
    for left, right in zip(knots, knots[1:]):
        wavelengths = (left + right) / 2 + (right - left) * nodes / 2
        product = np.ones_like(wavelengths)
        for curve in curves:
            values = np.interp(
                wavelengths,
                curve.wavelengths_nm,
                curve.values,
                left=0.0 if curve.outside_support == "zero" else None,
                right=0.0 if curve.outside_support == "zero" else None,
            )
            product *= values
        terms.append(float((right - left) / 2 * np.dot(weights, product)))
    return SpectralOracleResult(
        value=math.fsum(terms),
        unit=RADIANCE_UNIT if source.unit == SPECTRAL_RADIANCE_UNIT else "relative nm",
        wavelength_start_nm=wavelength_start_nm,
        wavelength_end_nm=wavelength_end_nm,
        quadrature_order=quadrature_order,
        interval_count=len(knots) - 1,
        source_ids=tuple(curve.source_id for curve in curves),
    )
