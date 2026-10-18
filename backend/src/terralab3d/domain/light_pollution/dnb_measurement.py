"""Operador espectral DNB: radiància integrada, sense inferència de font."""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date
from typing import Any


RADIANCE_UNIT = "nW cm^-2 sr^-1"
SPECTRAL_RADIANCE_UNIT = "nW cm^-2 sr^-1 nm^-1"
MEASUREMENT_OPERATOR_ID = "BAND_INTEGRATED"


def _check_wavelengths(wavelengths_nm: tuple[float, ...]) -> None:
    if len(wavelengths_nm) < 2 or any(not math.isfinite(x) for x in wavelengths_nm):
        raise ValueError("Calen almenys dues longituds d'ona finites")
    if any(right <= left for left, right in zip(wavelengths_nm, wavelengths_nm[1:])):
        raise ValueError("Les longituds d'ona han de ser estrictament creixents")


@dataclass(frozen=True, slots=True)
class ViirsSpectralResponse:
    platform: str
    product_id: str
    collection: str
    release_id: str
    gain_stage: str
    application: str
    valid_from: date
    valid_through: date
    wavelengths_nm: tuple[float, ...]
    relative_response: tuple[float, ...]
    source_url: str
    retrieved_at: str
    local_sha256: str
    redistribution_status: str
    evidence_class: str = "diagnostic_historical"
    l3_link_status: str = "unverified"
    spectral_uncertainty_status: str = "unquantified"
    gain_mapping_evidence: str | None = None
    source_checksum: str | None = None
    source_archive_sha256: str | None = None
    source_member: str | None = None
    source_member_sha256: str | None = None
    evidence_reference: str | None = None
    l3_link_evidence: str | None = None
    spectral_uncertainty_evidence: str | None = None

    def __post_init__(self) -> None:
        _check_wavelengths(self.wavelengths_nm)
        if len(self.wavelengths_nm) != len(self.relative_response):
            raise ValueError("La RSR i les longituds d'ona no tenen la mateixa mida")
        if any(not math.isfinite(x) for x in self.relative_response):
            raise ValueError("La RSR conté valors no finits")
        # Es conserven cues negatives de calibratge/rodoniment sense clipping.
        # Una corba així no és candidata operativa fins que se'n justifiqui el tractament.
        if not any(x > 0 for x in self.relative_response):
            raise ValueError("La RSR no té resposta positiva")
        if self.valid_through < self.valid_from:
            raise ValueError("L'interval de validesa de la RSR és invers")
        if self.evidence_class not in {
            "official_direct", "official_reconstructed", "official_recommended_proxy", "diagnostic_historical",
            "experimental", "uncertainty_family",
        }:
            raise ValueError("Classe d'evidència RSR desconeguda")
        if self.l3_link_status not in {"verified", "unverified"}:
            raise ValueError("Estat del vincle L3 desconegut")
        if self.spectral_uncertainty_status not in {"quantified", "unquantified"}:
            raise ValueError("Estat de la incertesa espectral desconegut")

    @property
    def source_model_candidate(self) -> bool:
        """Condicions necessàries de RSR/L3 per a 7.5; no acredita el model de font.

        La quantificació d'incertesa de producte correspon a 7.16. Aquesta
        propietat no exigeix una sigma fictícia per construir el SourceModel,
        però sí la correspondència espectral, de guany i de cadena L3.
        """
        return (
            self.application == "operational_l3"
            and self.evidence_class in {"official_direct", "official_reconstructed"}
            and self.l3_link_status == "verified"
            and bool(self.gain_mapping_evidence and self.gain_mapping_evidence.strip())
            and bool(self.evidence_reference and self.evidence_reference.strip())
            and bool(self.l3_link_evidence and self.l3_link_evidence.strip())
            and all(x >= 0 for x in self.relative_response)
        )

    @property
    def product_homologation_candidate(self) -> bool:
        """Una RSR sola no acredita la cadena completa L1B→L3."""
        return (
            self.source_model_candidate
            and self.spectral_uncertainty_status == "quantified"
            and self.spectral_uncertainty_evidence is not None
        )


@dataclass(frozen=True, slots=True)
class MeasurementTarget:
    """Identitat que impedeix aplicar una RSR a un altre producte o dia."""

    platform: str
    product_id: str
    collection: str
    acquisition_date: date

    def matches(self, response: ViirsSpectralResponse) -> bool:
        return (
            self.platform == response.platform
            and self.product_id == response.product_id
            and self.collection == response.collection
            and response.valid_from <= self.acquisition_date <= response.valid_through
        )


@dataclass(frozen=True, slots=True)
class SpectralRadiance:
    """Radiància espectral al sensor; no és una emissió hemisfèrica."""

    wavelengths_nm: tuple[float, ...]
    values_per_nm: tuple[float, ...]
    unit: str = SPECTRAL_RADIANCE_UNIT

    def __post_init__(self) -> None:
        _check_wavelengths(self.wavelengths_nm)
        if len(self.wavelengths_nm) != len(self.values_per_nm):
            raise ValueError("L'espectre i les longituds d'ona no tenen la mateixa mida")
        if self.unit != SPECTRAL_RADIANCE_UNIT:
            raise ValueError("Unitat de radiància espectral incompatible")
        if any(not math.isfinite(x) or x < 0 for x in self.values_per_nm):
            raise ValueError("La radiància espectral física ha de ser finita i no negativa")


@dataclass(frozen=True, slots=True)
class DnbBandMeasurement:
    radiance: float
    unit: str
    measurement_operator_id: str
    platform: str
    product_id: str
    collection: str
    rsr_release_id: str
    rsr_gain_stage: str
    rsr_application: str
    rsr_valid_from: date
    rsr_valid_through: date
    rsr_source_url: str
    rsr_retrieved_at: str
    rsr_local_sha256: str
    rsr_source_checksum: str | None
    rsr_source_archive_sha256: str | None
    rsr_source_member: str | None
    rsr_source_member_sha256: str | None
    rsr_redistribution_status: str
    rsr_evidence_class: str
    rsr_evidence_reference: str | None
    rsr_gain_mapping_evidence: str | None
    l3_link_status: str
    l3_link_evidence: str | None
    spectral_uncertainty_status: str
    spectral_uncertainty_evidence: str | None
    acquisition_date: date | None = None
    physical_stage: str = "at_sensor_toa"

    def to_dict(self) -> dict[str, Any]:
        """DTO JSON del resultat TOA, amb identitat i procedència de la RSR."""
        return {
            "schemaVersion": 1,
            "radiance": self.radiance,
            "unit": self.unit,
            "measurementOperatorId": self.measurement_operator_id,
            "physicalStage": self.physical_stage,
            "platform": self.platform,
            "productId": self.product_id,
            "collection": self.collection,
            "acquisitionDate": self.acquisition_date.isoformat() if self.acquisition_date else None,
            "rsrReleaseId": self.rsr_release_id,
            "rsrGainStage": self.rsr_gain_stage,
            "rsrApplication": self.rsr_application,
            "rsrValidFrom": self.rsr_valid_from.isoformat(),
            "rsrValidThrough": self.rsr_valid_through.isoformat(),
            "rsrSourceUrl": self.rsr_source_url,
            "rsrRetrievedAt": self.rsr_retrieved_at,
            "rsrLocalSha256": self.rsr_local_sha256,
            "rsrSourceChecksum": self.rsr_source_checksum,
            "rsrSourceArchiveSha256": self.rsr_source_archive_sha256,
            "rsrSourceMember": self.rsr_source_member,
            "rsrSourceMemberSha256": self.rsr_source_member_sha256,
            "rsrRedistributionStatus": self.rsr_redistribution_status,
            "rsrEvidenceClass": self.rsr_evidence_class,
            "rsrEvidenceReference": self.rsr_evidence_reference,
            "rsrGainMappingEvidence": self.rsr_gain_mapping_evidence,
            "l3LinkStatus": self.l3_link_status,
            "l3LinkEvidence": self.l3_link_evidence,
            "spectralUncertaintyStatus": self.spectral_uncertainty_status,
            "spectralUncertaintyEvidence": self.spectral_uncertainty_evidence,
        }


def _linear_at(x: float, knots: tuple[float, ...], values: tuple[float, ...]) -> float:
    index = min(bisect_right(knots, x) - 1, len(knots) - 2)
    left, right = knots[index], knots[index + 1]
    return values[index] + (values[index + 1] - values[index]) * (x - left) / (right - left)


class ViirsDnbMeasurementModel:
    """Integra dues funcions lineals a trossos sense renormalitzar la RSR."""

    def __init__(self, response: ViirsSpectralResponse, target: MeasurementTarget | None = None) -> None:
        if target is not None and not target.matches(response):
            raise ValueError("La RSR no correspon a la plataforma, producte, col·lecció o data")
        self.response = response
        self.target = target

    def measure(self, spectrum: SpectralRadiance) -> DnbBandMeasurement:
        response = self.response
        if (
            spectrum.wavelengths_nm[0] > response.wavelengths_nm[0]
            or spectrum.wavelengths_nm[-1] < response.wavelengths_nm[-1]
        ):
            raise ValueError("L'espectre no cobreix tot el suport tabulat de la RSR")
        knots = sorted(set(response.wavelengths_nm) | {
            x for x in spectrum.wavelengths_nm
            if response.wavelengths_nm[0] < x < response.wavelengths_nm[-1]
        })
        terms: list[float] = []
        for left, right in zip(knots, knots[1:]):
            s0 = _linear_at(left, spectrum.wavelengths_nm, spectrum.values_per_nm)
            s1 = _linear_at(right, spectrum.wavelengths_nm, spectrum.values_per_nm)
            r0 = _linear_at(left, response.wavelengths_nm, response.relative_response)
            r1 = _linear_at(right, response.wavelengths_nm, response.relative_response)
            ds, dr = s1 - s0, r1 - r0
            terms.append((right - left) * (s0 * r0 + (s0 * dr + r0 * ds) / 2 + ds * dr / 3))
        return DnbBandMeasurement(
            radiance=math.fsum(terms),
            unit=RADIANCE_UNIT,
            measurement_operator_id=MEASUREMENT_OPERATOR_ID,
            platform=response.platform,
            product_id=response.product_id,
            collection=response.collection,
            rsr_release_id=response.release_id,
            rsr_gain_stage=response.gain_stage,
            rsr_application=response.application,
            rsr_valid_from=response.valid_from,
            rsr_valid_through=response.valid_through,
            rsr_source_url=response.source_url,
            rsr_retrieved_at=response.retrieved_at,
            rsr_local_sha256=response.local_sha256,
            rsr_source_checksum=response.source_checksum,
            rsr_source_archive_sha256=response.source_archive_sha256,
            rsr_source_member=response.source_member,
            rsr_source_member_sha256=response.source_member_sha256,
            rsr_redistribution_status=response.redistribution_status,
            rsr_evidence_class=response.evidence_class,
            rsr_evidence_reference=response.evidence_reference,
            rsr_gain_mapping_evidence=response.gain_mapping_evidence,
            l3_link_status=response.l3_link_status,
            l3_link_evidence=response.l3_link_evidence,
            spectral_uncertainty_status=response.spectral_uncertainty_status,
            spectral_uncertainty_evidence=response.spectral_uncertainty_evidence,
            acquisition_date=self.target.acquisition_date if self.target else None,
        )
