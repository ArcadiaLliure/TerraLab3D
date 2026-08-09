"""Data-driven body catalogue contracts for the Step 8.6 Solar System."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .models import CoverageStatus, PhysicalModelQuality


@dataclass(frozen=True, slots=True)
class SolarSystemBodyDefinition:
    body_id: str
    naif_id: int | None
    name: str
    provisional_designation: str | None
    parent_naif_id: int
    parent_body_id: str
    spk_kernel_ids: tuple[str, ...]
    coverage_start_et: float | None
    coverage_end_et: float | None
    body_fixed_frame: str | None
    radii_km: tuple[float, float, float] | None
    mean_radius_km: float | None
    ephemeris_quality: PhysicalModelQuality
    orientation_quality: PhysicalModelQuality
    shape_quality: PhysicalModelQuality
    texture_quality: PhysicalModelQuality

    @property
    def has_spk(self) -> bool:
        return bool(self.spk_kernel_ids) and self.naif_id is not None

    def coverage_at(self, et: float) -> CoverageStatus:
        if not self.has_spk:
            return CoverageStatus.NO_KERNEL
        if self.coverage_start_et is None or self.coverage_end_et is None:
            return CoverageStatus.ERROR
        if self.coverage_start_et <= et <= self.coverage_end_et:
            return CoverageStatus.IN_RANGE
        return CoverageStatus.OUT_OF_RANGE

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SolarSystemBodyDefinition":
        radii = payload.get("radiiKm")
        return cls(
            body_id=str(payload["id"]),
            naif_id=_optional_int(payload.get("naifId")),
            name=str(payload.get("displayName") or payload.get("name") or payload["id"]),
            provisional_designation=_optional_string(payload.get("provisionalDesignation")),
            parent_naif_id=int(payload["parentNaifId"]),
            parent_body_id=str(payload["parentId"]),
            spk_kernel_ids=tuple(str(item) for item in payload.get("spkKernelIds", ())),
            coverage_start_et=_optional_float(payload.get("spkCoverageStartET")),
            coverage_end_et=_optional_float(payload.get("spkCoverageEndET")),
            body_fixed_frame=_optional_string(payload.get("bodyFixedFrame")),
            radii_km=(tuple(float(item) for item in radii) if radii is not None else None),  # type: ignore[arg-type]
            mean_radius_km=_optional_float(payload.get("meanRadiusKm")),
            ephemeris_quality=_quality(payload.get("ephemerisQuality")),
            orientation_quality=_quality(payload.get("orientationQuality")),
            shape_quality=_quality(payload.get("shapeQuality")),
            texture_quality=_quality(payload.get("textureQuality")),
        )


@dataclass(frozen=True, slots=True)
class SatelliteCatalogSnapshot:
    version: str
    catalog_date: str
    total_count: int
    by_parent: dict[str, int]
    satellites: tuple[SolarSystemBodyDefinition, ...]
    with_spk_count: int
    with_orientation_count: int
    with_radius_count: int

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SatelliteCatalogSnapshot":
        counts = payload["counts"]
        coverage = payload["coverage"]
        satellites = tuple(
            SolarSystemBodyDefinition.from_dict(item) for item in payload["satellites"]
        )
        return cls(
            version=str(payload["catalogVersion"]),
            catalog_date=str(payload["catalogDate"]),
            total_count=int(counts["total"]),
            by_parent={str(key): int(value) for key, value in counts["byParent"].items()},
            satellites=satellites,
            with_spk_count=int(coverage["withSpk"]),
            with_orientation_count=int(coverage["withOrientation"]),
            with_radius_count=int(coverage["withRadius"]),
        )

    def for_parents(self, parent_ids: Iterable[str]) -> tuple[SolarSystemBodyDefinition, ...]:
        selected = frozenset(parent_ids)
        return tuple(item for item in self.satellites if item.parent_body_id in selected)


@dataclass(frozen=True, slots=True)
class OrbitGeometry:
    body_id: str
    parent_body_id: str
    start_et: float
    end_et: float
    sample_count: int
    frame: str
    kernel_generation: str
    orbit_generation: int
    positions_parent_fixed_km: tuple[tuple[float, float, float], ...]


def _quality(value: Any) -> PhysicalModelQuality:
    try:
        return PhysicalModelQuality(str(value))
    except ValueError:
        return PhysicalModelQuality.UNAVAILABLE


def _optional_string(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def _optional_float(value: Any) -> float | None:
    return float(value) if value is not None else None
