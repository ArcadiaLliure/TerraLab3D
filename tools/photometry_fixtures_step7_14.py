"""Perfils científics explícits i models instrumentals provisionals de7.14."""

from pathlib import Path
import json

from terralab3d.domain.photometric_projection import GaussianFov, PhotometricResponse
from terralab3d.domain.light_pollution.spectral_oracle import (
    DIMENSIONLESS_UNIT,
    SpectralCurve,
)
from terralab3d.infrastructure.adapters.light_pollution.spectral_library import (
    load_spectral_library,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidencies/pas7.14"


def profiles() -> tuple[PhotometricResponse, ...]:
    library = load_spectral_library()
    result = [
        PhotometricResponse(
            "CIE-V-2019-tabulated",
            "CIE",
            SpectralCurve(
                "CIE-sle-photopic",
                library.photopic_wavelengths,
                library.photopic_values,
                DIMENSIONLESS_UNIT,
                "zero",
            ),
            "CIE photopic spectral luminous efficiency, taula empaquetada i metadades originals; Km=683 lm/W",
            sensor_profile_complete=True,
        )
    ]
    for data in json.loads((OUT / "models-resposta-referencia.json").read_text("utf8")):
        result.append(
            PhotometricResponse(
                data["responseId"],
                data["kind"],
                SpectralCurve(
                    data["responseId"],
                    tuple(data["wavelengthsNm"]),
                    tuple(data["energyResponse"]),
                    DIMENSIONLESS_UNIT,
                    "unavailable",
                ),
                data["provenance"],
                GaussianFov(
                    data["fovModelId"], data["nominalFwhmDeg"], data["fovProvenance"]
                ),
                data["zeroPointId"],
                False,
                tuple(data["limitations"]),
            )
        )
    return tuple(result)
