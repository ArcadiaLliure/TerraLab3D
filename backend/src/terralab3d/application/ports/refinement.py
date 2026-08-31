"""Ports protecting the external boundaries of TLST refinement workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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
from terralab3d.domain.refinement.licensing import LicenseMetadata


@dataclass(frozen=True, slots=True)
class ManualRefinementImportRequest:
    category_key: str
    category_codes: tuple[tuple[str, tuple[int, ...]], ...]
    resource_id: str
    variant_id: str
    source_id: str
    name: str
    indexed_path: Path
    original_crs: str
    fingerprint: str
    license: LicenseMetadata


class GeometryPort(CoverageGeometry, Protocol):
    def from_geojson(
        self,
        geometry: Mapping[str, object],
        *,
        source_crs: str,
        target_crs: str,
    ) -> MetricGeometry: ...

    def to_geojson(
        self,
        geometry: MetricGeometry,
        *,
        target_crs: str | None = None,
    ) -> dict[str, object]: ...

    def simplify_for_visualization(self, geometry: MetricGeometry) -> MetricGeometry: ...

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

    def remove(self, installation_id: str) -> RefinementInstallation | None: ...


class RefinementProcessorPort(Protocol):
    def verify_and_process(self, operation: object) -> object: ...


class ManualRefinementImportPort(Protocol):
    def register(
        self,
        request: ManualRefinementImportRequest,
    ) -> tuple[RefinementInstallation, ...]: ...

    def remove_resource(
        self,
        resource_id: str,
        variant_id: str,
    ) -> tuple[RefinementInstallation, ...]: ...


class RefinementProductCatalogPort(Protocol):
    def list_products(self, category_key: str) -> Sequence[RefinementProduct]: ...

    def list_all_products(self) -> Sequence[RefinementProduct]: ...

    def get_product(self, product_id: str) -> RefinementProduct | None: ...
