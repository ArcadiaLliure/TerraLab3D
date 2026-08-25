"""Ports protecting the external boundaries of TLST refinement workflows."""

from __future__ import annotations

from typing import Mapping, Protocol, Sequence

from terralab3d.domain.refinement.coverage import CoverageGeometry, MetricGeometry
from terralab3d.domain.refinement.discovery import (
    DiscoveredRefinementProduct,
    DiscoveryRequest,
)
from terralab3d.domain.refinement.installations import (
    RefinementInstallation,
    RefinementProduct,
)


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
    provider_id: str

    async def discover(
        self,
        request: DiscoveryRequest,
    ) -> Sequence[DiscoveredRefinementProduct]: ...


class RefinementCoverageRepositoryPort(Protocol):
    def list_installations(self) -> Sequence[RefinementInstallation]: ...

    def get(self, installation_id: str) -> RefinementInstallation | None: ...

    def upsert(self, installation: RefinementInstallation) -> None: ...


class RefinementProcessorPort(Protocol):
    def verify_and_process(self, operation: object) -> object: ...


class RefinementProductCatalogPort(Protocol):
    def list_products(self, category_key: str) -> Sequence[RefinementProduct]: ...

    def list_all_products(self) -> Sequence[RefinementProduct]: ...

    def get_product(self, product_id: str) -> RefinementProduct | None: ...
