"""Retenció espectral explícita i projeccions separades del transport."""

from __future__ import annotations

from dataclasses import replace
import math
from typing import Callable

from terralab3d.domain.light_pollution.adaptive_dome import AdaptiveDomeField
from terralab3d.domain.light_pollution.propagation_kernel import (
    PropagationCancelledError,
    PropagationKernel,
    PropagationRequest,
    PropagationResult,
    StalePropagationError,
)
from terralab3d.domain.light_pollution.spectral_oracle import (
    DIMENSIONLESS_UNIT,
    SpectralCurve,
)
from terralab3d.domain.photometric_projection import (
    BandSignal,
    PHOTOPIC_KM,
    PhotometricResponse,
    ProjectionUnavailable,
    photopic_luminance,
    project_band,
    sensor_magnitude,
)


def retain_spectrum(
    request: PropagationRequest,
    responses: tuple[PhotometricResponse, ...],
    *,
    cancelled: Callable[[], bool] | None = None,
    is_current: Callable[[], bool] | None = None,
) -> PropagationResult:
    """Una avaluació del mateix kernel per totes les respostes previstes.

    Afegeix els nusos de resposta a una banda plana. Retorna densitats per nm,
    no les divideix per V(λ) ni pressuposa espectre fora del suport de la font.
    """
    if request.spectral is None or not responses:
        raise ValueError("Cal transport espectral i respostes explícites")
    lo, hi = request.spectral.wavelength_start_nm, request.spectral.wavelength_end_nm
    knots = tuple(
        sorted(
            {lo, hi}
            | {w for r in responses for w in r.curve.wavelengths_nm if lo < w < hi}
        )
    )
    flat = SpectralCurve(
        "retained-spectrum-response-knot-union-v1",
        knots,
        (1.0,) * len(knots),
        DIMENSIONLESS_UNIT,
        "unavailable",
    )
    prepared = replace(request, spectral=replace(request.spectral, responses=(flat,)))
    return PropagationKernel().evaluate(
        prepared,
        capture_spectral_density=True,
        cancelled=cancelled,
        is_current=is_current,
    )


def project_retained(
    result: PropagationResult,
    responses: tuple[PhotometricResponse, ...],
    *,
    expected_revision: int,
    cancelled: Callable[[], bool] | None = None,
    is_current: Callable[[], bool] | None = None,
) -> dict[str, object]:
    """Consumeix exclusivament dades; no crida retain_spectrum ni el kernel."""

    def guard():
        if result.revision != expected_revision or (
            is_current is not None and not is_current()
        ):
            raise StalePropagationError("Projecció d’una revisió obsoleta")
        if cancelled is not None and cancelled():
            raise PropagationCancelledError("Projecció cancel·lada")

    guard()
    if not result.spectral_samples:
        raise ProjectionUnavailable(
            "El resultat escalar no conté radiància espectral retinguda"
        )
    grouped: dict[tuple[str, str], list[BandSignal]] = {}
    failures: dict[tuple[str, str], list[str]] = {}
    for samples in result.spectral_samples:
        for response in responses:
            guard()
            try:
                signal = project_band(samples, response)
                grouped.setdefault(
                    (samples.direction_id, response.response_id), []
                ).append(signal)
            except ProjectionUnavailable as exc:
                failures.setdefault(
                    (samples.direction_id, response.response_id), []
                ).append(str(exc))
    rows = []
    directions = sorted({s.direction_id for s in result.spectral_samples})
    for direction in directions:
        for response in responses:
            key = direction, response.response_id
            if key in failures:
                rows.append(
                    dict(
                        directionId=direction,
                        bandSignal=None,
                        projection=dict(
                            kind=response.kind,
                            status="unavailable",
                            value=None,
                            reason="; ".join(failures[key]),
                            spectralResponseId=response.response_id,
                        ),
                    )
                )
                continue
            components = grouped[key]
            first = components[0]
            if any(
                (s.unit, s.scale_id, s.domain_nm)
                != (first.unit, first.scale_id, first.domain_nm)
                for s in components
            ):
                raise ValueError(
                    "La suma de fonts requereix la mateixa escala i suport"
                )
            total = replace(
                first,
                value=math.fsum(s.value for s in components),
                los_error_estimate=math.fsum(s.los_error_estimate for s in components),
                source_id="sum:" + ",".join(s.source_id for s in components),
                band_set_id="sum:" + ",".join(s.band_set_id for s in components),
            )
            projection = (
                photopic_luminance(total)
                if response.kind == "CIE"
                else sensor_magnitude(total, response)
            )
            rows.append(
                dict(
                    directionId=direction,
                    sourceIds=[s.source_id for s in components],
                    bandSignal=total,
                    projection=projection,
                )
            )
    guard()
    return dict(
        revision=result.revision,
        inputSignature=result.input_signature,
        projections=rows,
        physicalTransportEvaluations=0,
        bortleEquivalent=None,
        bortlePolicyId=None,
    )


def cie_dome_luminance(
    field: AdaptiveDomeField,
    azimuth_deg: float,
    elevation_deg: float,
    *,
    field_response_id: str,
) -> dict[str, object]:
    if field_response_id != "CIE-V-2019-tabulated":
        raise ProjectionUnavailable("El DomeProfile no acredita la ponderació CIE V")
    value = field.evaluate(azimuth_deg, elevation_deg)
    if value is None:
        raise ProjectionUnavailable("Aquest interval exigeix transport directe")
    if field.radiance_unit not in {"W m^-2 sr^-1", "relative m^-2 sr^-1"}:
        raise ValueError("Unitat de DomeProfile incompatible")
    absolute = field.radiance_unit.startswith("W ")
    return dict(
        status="available" if absolute else "relative",
        value=PHOTOPIC_KM * value,
        unit="cd m^-2" if absolute else "relative (683 V-weighted)",
        revision=field.revision,
        topM=field.top_m,
        provenance=field.provenance,
    )


def dome_sensor_availability(
    field: AdaptiveDomeField,
    response: PhotometricResponse,
    *,
    field_response_id: str,
) -> dict[str, object]:
    reasons = []
    if field_response_id != response.response_id:
        reasons.append(
            "DomeProfile ponderat amb una altra resposta; no hi ha espectre recuperable"
        )
    if not response.sensor_profile_complete:
        reasons.extend(response.limitations)
    if response.fov is None:
        reasons.append("FOV absent")
    else:
        reasons.append(
            "FOV hemisfèric amb pes fora d’elevacions0,5–90°; manca una cota del domini absent"
        )
    if field.direct_only:
        reasons.append(
            "Visibilitat sense garanties d’interpolació: només nodes directes"
        )
    return dict(
        kind=response.kind,
        status="unavailable",
        value=None,
        reasons=reasons,
        revision=field.revision,
        spectralResponseId=response.response_id,
        physicalTransportEvaluations=0,
    )
