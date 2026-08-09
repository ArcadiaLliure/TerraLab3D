"""Persistent-generation orchestration for planetocentric SPK orbit samples."""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from typing import Protocol

from terralab3d.domain.solar_system.catalog import OrbitGeometry, SolarSystemBodyDefinition


class OrbitEphemerisPort(Protocol):
    def sample_orbit(
        self,
        definition: SolarSystemBodyDefinition,
        start_et: float,
        end_et: float,
        sample_count: int,
    ) -> OrbitGeometry: ...


@dataclass(frozen=True, slots=True)
class OrbitBinaryResource:
    resource_id: str
    version: str
    metadata: dict[str, object]
    payload: bytes


class OrbitSampler:
    """Caches SPK samples by their real scientific dependencies."""

    def __init__(self, ephemeris: OrbitEphemerisPort) -> None:
        self._ephemeris = ephemeris
        self._cache: dict[tuple[object, ...], OrbitGeometry] = {}
        self.sample_count = 0
        self.cache_hit_count = 0
        self.last_sampling_duration_ms = 0.0

    def sample(
        self,
        definition: SolarSystemBodyDefinition,
        start_et: float,
        end_et: float,
        sample_count: int,
        kernel_generation: str,
    ) -> OrbitGeometry:
        key = (
            definition.body_id,
            kernel_generation,
            float(start_et),
            float(end_et),
            int(sample_count),
            "J2000 planetocentric",
        )
        cached = self._cache.get(key)
        if cached is not None:
            self.cache_hit_count += 1
            return cached
        started = time.perf_counter()
        geometry = self._ephemeris.sample_orbit(
            definition, start_et, end_et, sample_count
        )
        self.last_sampling_duration_ms = (time.perf_counter() - started) * 1000.0
        self._cache[key] = geometry
        self.sample_count += 1
        return geometry

    @staticmethod
    def encode(geometry: OrbitGeometry) -> OrbitBinaryResource:
        values = (
            component
            for point in geometry.positions_parent_fixed_km
            for component in point
        )
        payload = struct.pack(
            f"<{geometry.sample_count * 3}f",
            *values,
        )
        metadata: dict[str, object] = {
            "resourceId": f"orbit:{geometry.body_id}",
            "version": str(geometry.orbit_generation),
            "role": "solar_system_orbit",
            "bodyId": geometry.body_id,
            "parentBodyId": geometry.parent_body_id,
            "startET": geometry.start_et,
            "endET": geometry.end_et,
            "sampleCount": geometry.sample_count,
            "frame": geometry.frame,
            "kernelGeneration": geometry.kernel_generation,
            "orbitGeneration": geometry.orbit_generation,
            "componentType": "float32",
            "componentsPerVertex": 3,
        }
        return OrbitBinaryResource(
            resource_id=str(metadata["resourceId"]),
            version=str(metadata["version"]),
            metadata=metadata,
            payload=payload,
        )

    def clear(self) -> None:
        self._cache.clear()
