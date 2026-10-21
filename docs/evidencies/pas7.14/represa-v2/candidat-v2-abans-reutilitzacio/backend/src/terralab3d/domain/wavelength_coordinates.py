"""Coordenades espectrals explícites; mai reinterpreta les taules heretades.

Ciddor/NIST per a aire sec a15°C i101325Pa. CIE018:2019 usa450ppm
(ISO/CIE11664-2:2022§3.5). La convenció històrica300ppm és diferenciada.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from typing import Literal

from .light_pollution.spectral_oracle import DIMENSIONLESS_UNIT, SpectralCurve

WavelengthBasis = Literal[
    "vacuum_nm", "standard_air_450ppm_nm", "standard_air_300ppm_nm"
]
COORDINATE_REVISION = "ciddor1996-standard-air-pullback-v2"


def standard_air_index(vacuum_nm: float, *, co2_ppm: float = 450.0) -> float:
    if not math.isfinite(vacuum_nm) or not 300 <= vacuum_nm <= 1700:
        raise ValueError("Ciddor/NIST: cal λ de buit entre300i1700nm")
    if co2_ppm not in (300.0, 450.0):
        raise ValueError("Cal convenció estàndard explícita300o450ppm; no aire ambient")
    s = (1000.0 / vacuum_nm) ** 2
    refractivity = 1e-8 * (5792105.0 / (238.0185 - s) + 167917.0 / (57.362 - s))
    return 1 + refractivity * (1 + 0.534e-6 * (co2_ppm - 450))


def air_from_vacuum(vacuum_nm: float, *, co2_ppm: float = 450.0) -> float:
    return vacuum_nm / standard_air_index(vacuum_nm, co2_ppm=co2_ppm)


def vacuum_from_air(air_nm: float, *, co2_ppm: float = 450.0) -> float:
    if not math.isfinite(air_nm) or not (
        air_from_vacuum(300.0, co2_ppm=co2_ppm)
        <= air_nm
        <= air_from_vacuum(1700.0, co2_ppm=co2_ppm)
    ):
        raise ValueError("Longitud d’ona en aire fora del domini Ciddor/NIST")
    v = min(1700.0, max(300.0, air_nm * 1.00028))
    for _ in range(12):
        updated = air_nm * standard_air_index(v, co2_ppm=co2_ppm)
        if abs(updated - v) <= 2e-12:
            return min(1700.0, max(300.0, updated))
        v = min(1700.0, max(300.0, updated))
    raise ArithmeticError("La inversió aire/buit no convergeix")


def air_jacobian(vacuum_nm: float, *, co2_ppm: float = 450.0) -> float:
    """dλ_air/dλ_vac: només multiplica densitats per nm, mai respostes."""
    n = standard_air_index(vacuum_nm, co2_ppm=co2_ppm)
    s = (1000.0 / vacuum_nm) ** 2
    dn = (
        1e-8
        * (1 + 0.534e-6 * (co2_ppm - 450))
        * (-2e6 / vacuum_nm**3)
        * (5792105.0 / (238.0185 - s) ** 2 + 167917.0 / (57.362 - s) ** 2)
    )
    return (n - vacuum_nm * dn) / n**2


@dataclass(frozen=True, slots=True)
class CoordinateCurve:
    curve: SpectralCurve
    basis: WavelengthBasis
    role: Literal["response", "density"]

    def __post_init__(self) -> None:
        if self.basis not in {
            "vacuum_nm",
            "standard_air_450ppm_nm",
            "standard_air_300ppm_nm",
        }:
            raise ValueError(
                "Convenció espectral absent o desconeguda; no s’infereix de nm"
            )
        if self.role not in {"response", "density"} or (
            (self.curve.unit == DIMENSIONLESS_UNIT) != (self.role == "response")
        ):
            raise ValueError("Cal distingir resposta adimensional de densitat per nm")
        if self.basis != "vacuum_nm":
            for w in (self.curve.wavelengths_nm[0], self.curve.wavelengths_nm[-1]):
                vacuum_from_air(w, co2_ppm=self.co2_ppm)

    @property
    def co2_ppm(self) -> float:
        return 300.0 if self.basis == "standard_air_300ppm_nm" else 450.0

    @property
    def vacuum_knots(self) -> tuple[float, ...]:
        if self.basis == "vacuum_nm":
            return self.curve.wavelengths_nm
        return tuple(
            vacuum_from_air(w, co2_ppm=self.co2_ppm) for w in self.curve.wavelengths_nm
        )

    def at_vacuum(self, vacuum_nm: float) -> float:
        if not math.isfinite(vacuum_nm):
            raise ValueError("Longitud d’ona no finita")
        native = (
            vacuum_nm
            if self.basis == "vacuum_nm"
            else air_from_vacuum(vacuum_nm, co2_ppm=self.co2_ppm)
        )
        c = self.curve
        if not c.wavelengths_nm[0] <= native <= c.wavelengths_nm[-1]:
            if c.outside_support == "zero":
                return 0.0
            raise ValueError("Suport desconegut: no es converteix en resposta nul·la")
        i = min(bisect_right(c.wavelengths_nm, native) - 1, len(c.values) - 2)
        a, b = c.wavelengths_nm[i : i + 2]
        value = c.values[i] + (c.values[i + 1] - c.values[i]) * (native - a) / (b - a)
        if self.role == "density" and self.basis != "vacuum_nm":
            value *= air_jacobian(vacuum_nm, co2_ppm=self.co2_ppm)
        return value

    def linearized_vacuum(
        self, *, peak_fraction: float = 1e-10, max_knots: int = 100000
    ) -> SpectralCurve:
        """Exportació versionada al contracte lineal existent, amb refinament local.

        El control de punt mitjà és un estimador de representació; l’oracle
        independent de la campanya en verifica també la integral. Cap transport.
        """
        if (
            not math.isfinite(peak_fraction)
            or peak_fraction <= 0
            or type(max_knots) is not int
            or max_knots < 2
        ):
            raise ValueError("Precisió o límit de representació invàlids")
        knots = self.vacuum_knots
        # Valors als nusos natius: evita extrapolar per una ULP en la inversió.
        values = [
            y
            * (
                air_jacobian(w, co2_ppm=self.co2_ppm)
                if self.role == "density" and self.basis != "vacuum_nm"
                else 1
            )
            for w, y in zip(knots, self.curve.values, strict=True)
        ]
        tolerance = peak_fraction * max(abs(y) for y in values)
        output = [(knots[0], values[0])]

        def append(a: float, b: float, ya: float, yb: float, depth: int) -> None:
            m = (a + b) / 2
            ym = self.at_vacuum(m)
            if abs(ym - (ya + yb) / 2) > tolerance:
                if depth >= 24:
                    raise ArithmeticError("Representació espectral no resolta")
                append(a, m, ya, ym, depth + 1)
                append(m, b, ym, yb, depth + 1)
            else:
                output.append((b, yb))
                if len(output) > max_knots:
                    raise ArithmeticError("Pressupost de nusos espectrals esgotat")

        for a, b, ya, yb in zip(knots, knots[1:], values, values[1:]):
            append(a, b, ya, yb, 0)
        return SpectralCurve(
            f"{self.curve.source_id}:{self.basis}:{self.role}:{COORDINATE_REVISION}",
            tuple(p[0] for p in output),
            tuple(p[1] for p in output),
            self.curve.unit,
            self.curve.outside_support,
        )
