"""Observació Black Marble L3 corregida de VNP46A2 Collection 2.

La radiància de DNB_BRDF-Corrected_NTL és la mostra de radiància nocturna
ascendent de superfície corregida segons Black Marble, no la radiància TOA.
No és una SPD, un flux hemisfèric ni una distribució angular de la font.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class Vnp46Policy:
    """Subconjunt immutable del manifest necessari per llegir una observació."""

    profile_id: str
    product_id: str
    collection: str
    layer: str
    radiance_unit: str
    fill_value: float
    valid_minimum: float
    quality_layer: str
    candidate_quality: frozenset[int]
    diagnostic_quality: frozenset[int]
    no_retrieval_quality: int
    ancillary_layers: tuple[str, ...]
    required_granule_attributes: tuple[str, ...]
    product_url: str
    doi: str

    @classmethod
    def from_profile(cls, profile: Mapping[str, Any]) -> Vnp46Policy:
        """Llegeix el contracte versionat; no hi ha defaults científics ocults."""

        source = profile["operationalSource"]
        temporal = profile["temporalPolicy"]
        low = profile["lowRadiancePolicy"]
        if (
            source["gapFilledLayerIsPrimary"]
            or temporal["selection"] != "exact_acquisition_day"
            or temporal["interpolation"] != "forbidden"
            or temporal["gapFilling"] != "forbidden_in_primary_observation"
            or low["silentClipping"]
        ):
            raise ValueError("El perfil VNP46 no respecta el contracte d'observació v1")
        return cls(
            profile_id=str(profile["profileId"]),
            product_id=str(source["productId"]),
            collection=str(source["collection"]),
            layer=str(source["primaryLayer"]),
            radiance_unit=str(source["radianceUnit"]),
            fill_value=float(source["fillValue"]),
            valid_minimum=float(source["validMinimumInclusive"]),
            quality_layer=str(source["qualityLayer"]),
            candidate_quality=frozenset(int(x) for x in source["candidateQualityValues"]),
            diagnostic_quality=frozenset(int(x) for x in source["diagnosticOnlyQualityValues"]),
            no_retrieval_quality=int(source["noRetrievalQualityValue"]),
            ancillary_layers=tuple(str(x) for x in source["additionalQualityLayers"]),
            required_granule_attributes=tuple(str(x) for x in source["granuleAttributesRequired"]),
            product_url=str(source["sourceUrl"]),
            doi=str(source["doi"]),
        )

    def classify(self, radiance: float, quality: int, *, is_fill: bool) -> str:
        """Qualifica la mostra sense alterar ni truncar el valor cru."""

        if is_fill or quality == self.no_retrieval_quality:
            return "no_retrieval"
        if radiance < self.valid_minimum:
            return "outside_valid_range"
        if quality in self.candidate_quality:
            return "candidate"
        if quality in self.diagnostic_quality:
            return "diagnostic_only"
        return "unknown_quality"


@dataclass(frozen=True, slots=True)
class Vnp46Provenance:
    granule_id: str
    sha256: str
    source_url: str | None
    product_url: str
    doi: str
    algorithm_version: str
    pge_version: str
    production_time: str
    range_beginning_date: str
    range_ending_date: str
    processing_center: str | None
    version_id: str | None
    tile_id: str | None
    horizontal_tile: str | None
    vertical_tile: str | None
    input_pointers: tuple[str, ...]
    radiance_dataset_path: str
    source_radiance_unit: str
    source_fill_value: float
    source_valid_range: str
    source_scale_factor: float | None
    source_offset: float | None

    def to_dict(self) -> dict[str, Any]:
        result = {field: getattr(self, field) for field in self.__dataclass_fields__}
        result["input_pointers"] = list(self.input_pointers)
        return result


@dataclass(frozen=True, slots=True)
class Vnp46Observation:
    schema_version: int
    profile_id: str
    product_id: str
    collection: str
    acquisition_date: date
    row: int
    column: int
    latitude_deg: float
    longitude_deg: float
    raw_radiance: float
    radiance_unit: str
    quality_flag: int
    qf_cloud_mask: int
    snow_flag: int
    latest_high_quality_retrieval: int
    is_fill: bool
    classification: str
    provenance: Vnp46Provenance

    @property
    def physical_stage(self) -> str:
        """Etapa física de la capa primària, separada de l'operador DNB TOA."""

        return "black_marble_l3_corrected_surface_upward_ntl"

    @property
    def source_inference_candidate(self) -> bool:
        """Només qualitat local QA; no acredita RSR, SPD o SourceModel."""

        return self.classification == "candidate"

    def to_dict(self) -> dict[str, Any]:
        """DTO JSON pur: la data i la procedència es representen explícitament."""

        return {
            "schemaVersion": self.schema_version,
            "profileId": self.profile_id,
            "productId": self.product_id,
            "collection": self.collection,
            "acquisitionDate": self.acquisition_date.isoformat(),
            "row": self.row,
            "column": self.column,
            "latitudeDeg": self.latitude_deg,
            "longitudeDeg": self.longitude_deg,
            "rawRadiance": self.raw_radiance,
            "radianceUnit": self.radiance_unit,
            "physicalStage": self.physical_stage,
            "qualityFlag": self.quality_flag,
            "qfCloudMask": self.qf_cloud_mask,
            "snowFlag": self.snow_flag,
            "latestHighQualityRetrieval": self.latest_high_quality_retrieval,
            "isFill": self.is_fill,
            "classification": self.classification,
            "sourceInferenceCandidate": self.source_inference_candidate,
            "provenance": self.provenance.to_dict(),
        }
