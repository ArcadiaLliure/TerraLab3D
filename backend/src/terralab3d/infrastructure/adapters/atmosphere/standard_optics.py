"""Atmosfera seca COESA 1975, NASA TR R-459 (1976), domini 0–50 km.

Constants/taula 3 i equacions hidrostàtiques de la font primària. No és
una observació, ni defineix aerosols, espectres d'absorció o coeficients β.
"""

from __future__ import annotations

import math
from bisect import bisect_right

from terralab3d.application.ports.atmospheric_optics import OpticalFieldRequest
from terralab3d.domain.light_pollution.optical_field import (
    FieldProvenance,
    OpticalField,
    OpticalTile,
    VerticalProfile,
)

MODEL_REVISION = "coesa1975-nasa-tr459-dry-0-50km-v1"
SOURCE_URL = "https://ntrs.nasa.gov/api/citations/19760017709/downloads/19760017709.pdf"
GEOPOTENTIAL_RADIUS_M = 6356766.0
_BASES = (0.0, 11000.0, 20000.0, 32000.0, 47000.0, 51000.0)
_LAPSES = (-0.0065, 0.0, 0.001, 0.0028, 0.0)
_GRAVITY_M_S2 = 9.80665
_MOLAR_MASS_KG_MOL = 0.0289644
_GAS_CONSTANT_J_MOL_K = 8.31432


def standard_pressure_temperature(height_m: float) -> tuple[float, float]:
    """Solució analítica en altura geomètrica; P en Pa i T en K."""
    if not math.isfinite(height_m) or not 0 <= height_m <= 50000:
        raise ValueError("COESA inferior admet només 0–50.000 m geomètrics")
    h = GEOPOTENTIAL_RADIUS_M * height_m / (GEOPOTENTIAL_RADIUS_M + height_m)
    layer = min(bisect_right(_BASES, h) - 1, len(_LAPSES) - 1)
    pressure, temperature = 101325.0, 288.15
    coefficient = _GRAVITY_M_S2 * _MOLAR_MASS_KG_MOL / _GAS_CONSTANT_J_MOL_K
    for i in range(layer + 1):
        dz = (h if i == layer else _BASES[i + 1]) - _BASES[i]
        lapse = _LAPSES[i]
        target = temperature + lapse * dz
        pressure *= (
            math.exp(-coefficient * dz / temperature)
            if lapse == 0
            else (temperature / target) ** (coefficient / lapse)
        )
        temperature = target
    return pressure, temperature


class StandardAtmosphericOpticsProvider:
    """Materialitza perfils tabulats; sense xarxa, cache radiativa ni serveis."""

    top_limit_m = 50000.0
    model_revision = MODEL_REVISION
    base_heights_m = _BASES
    pressure_temperature = staticmethod(standard_pressure_temperature)

    def resolve(self, request: OpticalFieldRequest) -> OpticalField:
        if request.top_m > self.top_limit_m:
            raise ValueError(
                "El provider estàndard no extrapola fora del domini declarat"
            )
        count = math.ceil(request.top_m / request.vertical_step_m)
        if count + len(self.base_heights_m) + 1 > 4096:
            raise ValueError(
                "El perfil sol·licitat excedeix el pressupost de 4.096 nusos"
            )
        knots = {
            0.0,
            request.top_m,
            *(i * request.vertical_step_m for i in range(1, count)),
        }
        for h in self.base_heights_m[1:]:
            z = GEOPOTENTIAL_RADIUS_M * h / (GEOPOTENTIAL_RADIUS_M - h)
            if z < request.top_m:
                knots.add(z)
        heights = tuple(sorted(knots))
        values = [self.pressure_temperature(z) for z in heights]
        provenance = tuple(
            FieldProvenance(
                name, "standard_coesa", self.model_revision, reference, interpretation
            )
            for name, reference, interpretation in (
                (
                    "pressure",
                    SOURCE_URL,
                    "Hidrostàtica ideal seca; Pa; interpolació log-lineal entre nusos",
                ),
                (
                    "temperature",
                    SOURCE_URL,
                    "Taula 3 en altura geopotencial; K; interpolació lineal en altura geomètrica",
                ),
                (
                    "relative_humidity",
                    SOURCE_URL,
                    "Hipòtesi prescrita d’aire sec: RH=0, no observació meteorològica",
                ),
                (
                    "number_density",
                    "https://physics.nist.gov/cgi-bin/cuu/Value?k%7Csearch_for=Boltzmann",
                    "n=P/(k_B T), k_B SI exacte actual; no s’usa el k històric de 1975",
                ),
            )
        )
        profile = VerticalProfile(
            heights,
            tuple(p for p, _ in values),
            tuple(t for _, t in values),
            self.model_revision,
            provenance,
        )
        return OpticalField(
            request.origin,
            tuple(
                OpticalTile(t.tile_id, t.version, t.bounds, profile)
                for t in request.tiles
            ),
            request.time_utc,
            request.radius_m,
        )


def extended_standard_pressure_temperature(height_m: float) -> tuple[float, float]:
    """COESA fins a 75 km: taula 3, sense extrapolar ni congelar T a la LUT.

    Per sota de 50 km delega exactament a la implementació històrica.
    No defineix l'exosfera ni declara nul·la la contribució superior.
    """
    if not math.isfinite(height_m) or not 0 <= height_m <= 75000:
        raise ValueError("COESA ampliat admet només 0–75.000 m geomètrics")
    if height_m <= 50000:
        return standard_pressure_temperature(height_m)
    bases = (*_BASES, 71000.0, 84852.0)
    lapses = (*_LAPSES, -0.0028, -0.002)
    h = GEOPOTENTIAL_RADIUS_M * height_m / (GEOPOTENTIAL_RADIUS_M + height_m)
    layer = min(bisect_right(bases, h) - 1, len(lapses) - 1)
    pressure, temperature = 101325.0, 288.15
    coefficient = _GRAVITY_M_S2 * _MOLAR_MASS_KG_MOL / _GAS_CONSTANT_J_MOL_K
    for i in range(layer + 1):
        dz = (h if i == layer else bases[i + 1]) - bases[i]
        target = temperature + lapses[i] * dz
        pressure *= (
            math.exp(-coefficient * dz / temperature)
            if lapses[i] == 0
            else (temperature / target) ** (coefficient / lapses[i])
        )
        temperature = target
    return pressure, temperature


class ExtendedStandardAtmosphericOpticsProvider(StandardAtmosphericOpticsProvider):
    """Ampliació optativa; el provider 0–50 km i les seves identitats es conserven."""

    top_limit_m = 75000.0
    model_revision = "coesa1975-nasa-tr459-dry-0-75km-v1"
    base_heights_m = (*_BASES, 71000.0, 84852.0)
    pressure_temperature = staticmethod(extended_standard_pressure_temperature)
