"""Model fotogràfic empíric V1, explícit i reproduïble.

El model estima profunditat de detecció; no és una radiometria completa. El seu
índex de fotons conserva la dependència física D²·t·T i deixa ISO fora del flux.
"""

from __future__ import annotations

import math

from terralab3d.domain.imaging.models import PhotographicLimitingMagnitudeInputs
from terralab3d.domain.optics.calculations import OpticalValidationError
from terralab3d.domain.optics.models import PhotographicPreview


class PhotographicLimitingMagnitudeModelV1:
    MODEL_ID = "terralab.photographic-limiting-magnitude.v1"

    def compute(self, values: PhotographicLimitingMagnitudeInputs) -> PhotographicPreview:
        focal = self._positive("focalLengthMm", values.focal_length_mm)
        f_number = self._positive("fNumber", values.f_number)
        iso = self._positive("iso", values.iso)
        exposure = self._positive("exposureSeconds", values.exposure_seconds)
        atmosphere_loss = float(values.atmospheric_loss_magnitude)
        eye_limit = float(values.eye_limit_magnitude)
        if not math.isfinite(atmosphere_loss) or atmosphere_loss < 0.0:
            raise OpticalValidationError("atmosphericLossMagnitude", "la pèrdua atmosfèrica ha de ser finita i no negativa")
        if not math.isfinite(eye_limit):
            raise OpticalValidationError("eyeLimitMagnitude", "la magnitud visual ha de ser finita")
        optics = 1.0 if values.optical_transmission is None else float(values.optical_transmission)
        if not math.isfinite(optics) or not 0.0 < optics <= 1.0:
            raise OpticalValidationError("opticalTransmission", "la transmissió òptica ha d'estar dins (0, 1]")

        aperture = focal / f_number
        atmosphere = 10.0 ** (-0.4 * atmosphere_loss)
        total_transmission = optics * atmosphere
        captured_photon_index = aperture**2 * exposure * total_transmission
        iso_gain = self._iso_detection_gain(iso)
        short_penalty = 0.0 if exposure >= 5.0 else 1.6 * math.log10(5.0 / exposure)
        sky_penalty = max(0.0, 7.6 - eye_limit)
        raw = (
            3.4
            + 2.5 * math.log10(aperture**2)
            + 1.25 * math.log10(exposure)
            + iso_gain
            + 2.5 * math.log10(total_transmission)
            - short_penalty
        )
        estimated = max(-12.0, min(22.0, raw - sky_penalty))
        return PhotographicPreview(
            model_id=self.MODEL_ID,
            estimated_limit_magnitude=estimated,
            captured_photon_index=captured_photon_index,
            iso_detection_gain_magnitude=iso_gain,
            atmospheric_transmission=atmosphere,
            total_transmission=total_transmission,
            short_exposure_penalty_magnitude=short_penalty,
            sky_penalty_magnitude=sky_penalty,
        )

    @staticmethod
    def _positive(field: str, value: float) -> float:
        number = float(value)
        if not math.isfinite(number) or number <= 0.0:
            raise OpticalValidationError(field, f"{field} ha de ser finit i estrictament positiu")
        return number

    @staticmethod
    def _iso_detection_gain(iso: float) -> float:
        if iso <= 100.0:
            return 1.25 * math.log10(iso)
        stops = math.log2(iso / 100.0)
        effective_stops = min(stops, 3.0) + 0.25 * max(0.0, stops - 3.0)
        return 2.5 + 1.25 * math.log10(2.0) * effective_stops
