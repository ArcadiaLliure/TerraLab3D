"""Port per resoldre una RSR VIIRS DNB de procedència explícita."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from terralab3d.domain.light_pollution.dnb_measurement import ViirsSpectralResponse


class ViirsSpectralResponseRepository(Protocol):
    def resolve(
        self,
        *,
        platform: str,
        product_id: str,
        collection: str,
        release_id: str,
        gain_stage: str,
        acquisition_date: date,
        application: str,
    ) -> ViirsSpectralResponse: ...
