"""Connexió local verificada NOAA-20 → fonts de transport condicionades."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

from terralab3d.domain.light_pollution.simulation import (
    ConditionalScenario,
    SkyglowConfiguration,
    build_conditional_scenarios,
)
from terralab3d.domain.light_pollution.vnp46 import Vnp46Policy
from .spectral_library import load_spectral_library
from .viirs_rsr import LocalViirsSpectralResponseRepository
from .vnp46 import Vnp46GranuleAdapter


def noaa20_policy(policy: Vnp46Policy) -> Vnp46Policy:
    """Mateix contracte numèric C2 verificat, identitat de producte distinta."""
    return replace(
        policy,
        profile_id="black-marble-noaa20-c2-v1",
        product_id="VJ146A2",
        product_url="https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VJ146A2",
        doi="10.5067/VIIRS/VJ146A2.002",
        required_granule_attributes=tuple(
            dict.fromkeys(
                (
                    *policy.required_granule_attributes,
                    "PlatformShortName",
                    "ShortName",
                    "VersionID",
                    "identifier_product_doi",
                )
            )
        ),
    )


def read_conditional_sources(
    path: Path,
    expected_sha256: str,
    policy: Vnp46Policy,
    acquisition_date: date,
    row: int,
    column: int,
    rsr_manifest: Path,
    configuration: SkyglowConfiguration,
    *,
    gain_stage: str = "MGS",
) -> tuple[ConditionalScenario, ...]:
    with Vnp46GranuleAdapter(
        path, policy=noaa20_policy(policy), expected_sha256=expected_sha256
    ) as reader:
        observation = reader.read_pixel(acquisition_date, row, column)
    response = LocalViirsSpectralResponseRepository(rsr_manifest).resolve_reference(
        platform="NOAA-20", gain_stage=gain_stage
    )
    return build_conditional_scenarios(
        observation, response, load_spectral_library(), configuration
    )
