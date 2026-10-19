"""Fases normalitzades i òptica monocromàtica prescrita per al B1 escalar."""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import asdict, dataclass, field
from typing import Literal

from .gauss_kronrod import QuadratureSettings
from .optical_field import OpticalState, fingerprint

RAYLEIGH_SOURCE = "https://lweb.cfa.harvard.edu/atmosphere/publications/1997AOring.pdf"


@dataclass(frozen=True, slots=True)
class PhaseFunction:
    kind: Literal["isotropic", "rayleigh", "hg_fallback", "tabulated"]
    evidence_reference: str
    asymmetry: float = 0.0
    depolarization_delta: float = 0.0
    cosines: tuple[float, ...] = ()
    relative_values: tuple[float, ...] = ()
    normalization: float = field(init=False, default=1.0)

    def __post_init__(self) -> None:
        if (
            self.kind not in {"isotropic", "rayleigh", "hg_fallback", "tabulated"}
            or not self.evidence_reference
            or not math.isfinite(self.asymmetry)
            or abs(self.asymmetry) >= 1
            or not math.isfinite(self.depolarization_delta)
            or not 0 <= self.depolarization_delta <= 1
        ):
            raise ValueError("Fase sense procedència o paràmetres no físics")
        if self.kind == "tabulated":
            if (
                len(self.cosines) < 3
                or len(self.cosines) != len(self.relative_values)
                or self.cosines[0] != -1
                or self.cosines[-1] != 1
                or any(b <= a for a, b in zip(self.cosines, self.cosines[1:]))
                or any(
                    not math.isfinite(x) for x in (*self.cosines, *self.relative_values)
                )
                or min(self.relative_values) < 0
            ):
                raise ValueError("Taula de fase no finita, negativa o incompleta")
            norm = (
                2
                * math.pi
                * math.fsum(
                    (b - a) * (x + y) / 2
                    for a, b, x, y in zip(
                        self.cosines,
                        self.cosines[1:],
                        self.relative_values,
                        self.relative_values[1:],
                    )
                )
            )
            if not math.isfinite(norm) or norm <= 0:
                raise ValueError("La fase tabulada té integral nul·la/no finita")
            object.__setattr__(self, "normalization", norm)

    def density(self, cosine: float) -> float:
        """Densitat en sr⁻¹; μ=1 és dispersió endavant."""
        if not math.isfinite(cosine) or not -1 - 2e-15 <= cosine <= 1 + 2e-15:
            raise ValueError("Cosinus de dispersió fora de [-1,1]")
        mu = max(-1.0, min(1.0, cosine))
        if self.kind == "isotropic":
            return 1 / (4 * math.pi)
        if self.kind == "rayleigh":
            d = self.depolarization_delta
            return 3 * ((1 + 3 * d) + (1 - d) * mu * mu) / (16 * math.pi * (1 + 2 * d))
        if self.kind == "hg_fallback":
            g = self.asymmetry
            denominator = (1 - abs(g)) ** 2 + 2 * abs(g) * (
                1 - math.copysign(1, g) * mu
            )
            return (1 - g * g) / (4 * math.pi * denominator**1.5)
        i = min(bisect_right(self.cosines, mu) - 1, len(self.cosines) - 2)
        f = (mu - self.cosines[i]) / (self.cosines[i + 1] - self.cosines[i])
        return (
            (1 - f) * self.relative_values[i] + f * self.relative_values[i + 1]
        ) / self.normalization


def dry_air_rayleigh(wavelength_nm: float) -> tuple[float, PhaseFunction]:
    """Chance–Spurr 1997, eq. 2–7: σ (m²) i fase amb despolarització coherent.

    Ajust publicat 200–1000 nm; dispersió escalar quasi-elàstica agregada.
    No simula línies Raman ni polarització. Constants històriques de la font.
    """
    if not math.isfinite(wavelength_nm) or not 200 <= wavelength_nm <= 1000:
        raise ValueError("Rayleigh Chance–Spurr només admet 200–1000 nm")
    s2 = (1000 / wavelength_nm) ** 2
    sigma = 3.9993e-32 * s2 * s2 / (1 - 1.069e-2 * s2 - 6.681e-5 * s2 * s2)
    refractivity = (0.7041 + 315.90 / (157.39 - s2) + 8.4127 / (50.429 - s2)) * 1e-4
    king = (
        sigma
        * 3
        * (2.686763e25) ** 2
        * (wavelength_nm * 1e-9) ** 4
        / (32 * math.pi**3 * refractivity**2)
    )
    rho = 6 * (king - 1) / (7 * king + 3)
    delta = rho / (2 - rho)
    return sigma, PhaseFunction("rayleigh", RAYLEIGH_SOURCE, depolarization_delta=delta)


@dataclass(frozen=True, slots=True)
class AerosolReference:
    tile_id: str
    version: str
    extinction_per_m: float
    single_scattering_albedo: float
    phase: PhaseFunction
    evidence_reference: str
    scale_height_m: float | None = None

    def __post_init__(self) -> None:
        if (
            not self.tile_id
            or not self.version
            or not self.evidence_reference
            or not math.isfinite(self.extinction_per_m)
            or self.extinction_per_m < 0
            or not math.isfinite(self.single_scattering_albedo)
            or not 0 <= self.single_scattering_albedo <= 1
            or self.scale_height_m is not None
            and (not math.isfinite(self.scale_height_m) or self.scale_height_m <= 0)
        ):
            raise ValueError("Aerosol de referència incomplet o no físic")

    def extinction(self, height_m: float) -> float:
        return self.extinction_per_m * (
            math.exp(-height_m / self.scale_height_m) if self.scale_height_m else 1.0
        )


@dataclass(frozen=True, slots=True)
class ScatteringBand:
    wavelength_nm: float
    rayleigh_cross_section_m2: float
    rayleigh_phase: PhaseFunction
    aerosols: tuple[AerosolReference, ...]
    evidence_reference: str
    revision: str = "single-scattering-monochromatic-v1"

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.wavelength_nm)
            or self.wavelength_nm <= 0
            or not math.isfinite(self.rayleigh_cross_section_m2)
            or self.rayleigh_cross_section_m2 < 0
            or not self.evidence_reference
            or self.revision != "single-scattering-monochromatic-v1"
            or not self.aerosols
            or len({a.tile_id for a in self.aerosols}) != len(self.aerosols)
        ):
            raise ValueError("Banda de dispersió no finita o incompleta")

    def aerosol(self, tile_id: str) -> AerosolReference:
        for a in self.aerosols:
            if a.tile_id == tile_id:
                return a
        raise ValueError("Falta estat aerosol explícit per al tile")

    @property
    def signature(self) -> str:
        return fingerprint(asdict(self))

    def coefficients(self, state: OpticalState) -> tuple[float, float, float]:
        aerosol = self.aerosol(state.dependency.tile_id)
        rayleigh = state.number_density_m3 * self.rayleigh_cross_section_m2
        ext = aerosol.extinction(state.altitude_m)
        return rayleigh, ext, ext * aerosol.single_scattering_albedo


@dataclass(frozen=True, slots=True)
class ScatteringConfiguration:
    band: ScatteringBand
    path_quadrature: QuadratureSettings = QuadratureSettings(1e-7, 1e-10, 4096)
    area_order: int = 2
    radiance_quadrature: QuadratureSettings = QuadratureSettings(1e-7, 1e-24, 4096)

    def __post_init__(self) -> None:
        if type(self.area_order) is not int or not 2 <= self.area_order <= 64:
            raise ValueError("Ordre d'àrea directe fora de 2–64")
