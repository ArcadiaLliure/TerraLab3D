"""Estat de configuració científic; cap resultat de transport fictici."""

from __future__ import annotations

import asyncio
from typing import Any

from terralab3d.domain.light_pollution.simulation import SkyglowConfiguration
from terralab3d.domain.light_pollution.spectral_library import SpectralLibrary


class SkyglowConfigurationController:
    def __init__(self, library: SpectralLibrary) -> None:
        self.library = library
        self.configuration = SkyglowConfiguration()
        self.generation = 0
        self.effective_spectrum: dict[str, Any] | None = None
        self.error: str | None = None

    async def configure(self, payload: dict[str, Any]) -> None:
        configuration = SkyglowConfiguration.from_dict(payload)
        self.generation += 1
        generation = self.generation
        self.configuration = configuration
        self.effective_spectrum = None
        self.error = None
        if configuration.mode == "kelvin":
            spectrum = await asyncio.to_thread(
                self.library.kelvin_spectrum,
                configuration.kelvin,
                configuration.spectral_family,
            )
            color = await asyncio.to_thread(self.library.colorimetry, spectrum)
            if generation != self.generation:
                return
            self.effective_spectrum = {
                "spectrumId": spectrum.spectrum_id,
                "components": spectrum.components,
                "effectiveCctK": color.cct_k,
                "distanceUv": color.distance_uv,
            }

    def snapshot(self) -> dict[str, Any]:
        return {
            "type": "skyglow_configuration_snapshot",
            "schemaVersion": 1,
            "generation": self.generation,
            "configuration": self.configuration.to_dict(),
            "configurationKey": self.configuration.cache_key,
            "spectralRevision": self.library.revision,
            "effectiveSpectrum": self.effective_spectrum,
            "mixtureBasis": "radiant_flux",
            "scientificQuality": "conditional_relative",
            "calculationStatus": "transport_pending",
            "blackMarble": None,
            "rsr": None,
            "skyRadiance": None,
            "error": self.error,
        }
