"""Ports protecting the external boundaries of TLST refinement workflows."""

from __future__ import annotations

from typing import Mapping, Protocol, Sequence

from terralab3d.domain.refinement.coverage import CoverageGeometry, MetricGeometry


class GeometryPort(CoverageGeometry, Protocol):
    def from_geojson(
        self,
        geometry: Mapping[str, object],
        *,
        source_crs: str,
        target_crs: str,
    ) -> MetricGeometry: ...

    def to_geojson(self, geometry: MetricGeometry) -> dict[str, object]: ...

    def reproject(self, geometry: MetricGeometry, target_crs: str) -> MetricGeometry: ...


class RefinementProviderPort(Protocol):
    def discover(self, category_key: str, aoi: Mapping[str, object]) -> Sequence[object]: ...


class RefinementCoverageRepositoryPort(Protocol):
    def list_installations(self) -> Sequence[object]: ...

    def upsert(self, installation: object) -> None: ...


class RefinementProcessorPort(Protocol):
    def verify_and_process(self, operation: object) -> object: ...


class RefinementProductCatalogPort(Protocol):
    def list_products(self, category_key: str) -> Sequence[object]: ...
