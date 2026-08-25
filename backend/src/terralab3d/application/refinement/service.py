"""Linear use cases for cataloguing and installing TLST refinements."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from terralab3d.application.ports.refinement import (
    RefinementCoverageRepositoryPort,
    RefinementProductCatalogPort,
)
from terralab3d.domain.refinement.errors import RefinementValidationError
from terralab3d.domain.refinement.installations import (
    CoverageVerificationMethod,
    GeometryRecord,
    RefinementInstallation,
    RefinementProduct,
    TechnicalResourceState,
)
from terralab3d.domain.refinement.licensing import CommercialLicensePolicy, LicenseUseStage
from terralab3d.domain.refinement.states import SpatialCoverageState, aggregate_coverage_states
from terralab3d.domain.surface.tlst import TaxonomyCatalog


@dataclass(frozen=True, slots=True)
class RefinementWorkspaceNode:
    category_key: str
    parent_key: str | None
    label: str
    state: SpatialCoverageState
    installation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RefinementWorkspace:
    taxonomy_key: str
    taxonomy_version: str
    virtual_root: str
    nodes: tuple[RefinementWorkspaceNode, ...]


class RefinementService:
    """Coordinate the phase-1 workflow without knowing providers or JSON."""

    def __init__(
        self,
        taxonomy: TaxonomyCatalog,
        repository: RefinementCoverageRepositoryPort,
        product_catalog: RefinementProductCatalogPort,
        license_policy: CommercialLicensePolicy,
        data_root: Path,
        *,
        labels: Mapping[str, str] | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._taxonomy = taxonomy
        self._repository = repository
        self._product_catalog = product_catalog
        self._license_policy = license_policy
        self._data_root = data_root
        self._labels = dict(labels or {})
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: uuid4().hex)

    def selectable_products(self, category_key: str) -> tuple[RefinementProduct, ...]:
        canonical = self._taxonomy.canonical_category_key(category_key)
        candidates = self._product_catalog.list_products(canonical)
        result: list[RefinementProduct] = []
        for product in candidates:
            decision = self._license_policy.evaluate(
                product.license,
                stage=LicenseUseStage.CATALOG_DISPLAY,
            )
            if decision.allowed and self._is_compatible(canonical, product):
                result.append(product)
        return tuple(sorted(result, key=lambda value: (value.priority, value.product_id)))

    def workspace(self) -> RefinementWorkspace:
        installations = tuple(self._repository.list_installations())
        known_nodes = {
            node
            for product in self._product_catalog.list_all_products()
            for node in product.tlst_nodes
            if node in self._taxonomy.category_keys
        }
        direct_installations: dict[str, list[RefinementInstallation]] = {}
        for installation in installations:
            for node in installation.tlst_nodes:
                if node in self._taxonomy.category_keys:
                    direct_installations.setdefault(node, []).append(installation)

        state_by_key: dict[str, SpatialCoverageState] = {}
        ids_by_key: dict[str, tuple[str, ...]] = {}
        ordered = sorted(
            self._taxonomy.categories,
            key=lambda item: item.key.count("."),
            reverse=True,
        )
        for category in ordered:
            direct = direct_installations.get(category.key, [])
            direct_states = [item.spatial_state for item in direct]
            child_states = [
                state_by_key[child]
                for child in self._taxonomy.direct_children(category.key)
            ]
            states = [*direct_states, *child_states]
            if states:
                state = aggregate_coverage_states(states)
            elif category.key in known_nodes:
                state = SpatialCoverageState.ABSENT
            else:
                state = SpatialCoverageState.NOT_APPLICABLE
            state_by_key[category.key] = state
            ids_by_key[category.key] = tuple(sorted(item.installation_id for item in direct))

        nodes = tuple(
            RefinementWorkspaceNode(
                category_key=category.key,
                parent_key=category.parent_key,
                label=self._labels.get(category.key, category.key),
                state=state_by_key[category.key],
                installation_ids=ids_by_key[category.key],
            )
            for category in self._taxonomy.categories
        )
        return RefinementWorkspace(
            taxonomy_key=self._taxonomy.taxonomy_key,
            taxonomy_version=self._taxonomy.taxonomy_version,
            virtual_root="surface",
            nodes=nodes,
        )

    def confirm_operation(
        self,
        *,
        product_id: str,
        category_key: str,
        aoi_id: str,
        job_id: str,
    ) -> RefinementInstallation:
        canonical = self._taxonomy.canonical_category_key(category_key)
        product = self._product_catalog.get_product(product_id)
        if product is None or not self._is_compatible(canonical, product):
            raise RefinementValidationError(
                f"Product {product_id!r} cannot refine {canonical!r}"
            )
        self._license_policy.require_allowed(
            product.license,
            stage=LicenseUseStage.JOB_START,
        )
        installation_id = self._id_factory()
        local_path = build_refinement_install_path(
            self._data_root,
            category_key=canonical,
            provider=product.provider,
            product=product.product,
            version=product.version,
            aoi_id=aoi_id,
        )
        installation = RefinementInstallation(
            installation_id=installation_id,
            resource_id=product.resource_id,
            variant_id=product.variant_id,
            provider=product.provider,
            product=product.product,
            version=product.version,
            tlst_nodes=product.tlst_nodes,
            data_kind=product.data_kind,
            local_path=str(local_path),
            planned_geometry=product.planned_geometry,
            verified_geometry=None,
            original_crs=product.original_crs,
            created_at=self._clock(),
            installed_at=None,
            technical_state=TechnicalResourceState.QUEUED,
            spatial_state=SpatialCoverageState.PARTIAL,
            job_id=job_id,
            license=product.license,
            provenance_url=product.provenance_url,
            file_fingerprints=(),
            verification_method=None,
            aoi_id=aoi_id,
        )
        self._repository.upsert(installation)
        return installation

    def register_verified_coverage(
        self,
        installation_id: str,
        *,
        verified_geometry: GeometryRecord,
        verified_ratio: float,
        file_fingerprints: Sequence[str],
        method: CoverageVerificationMethod,
    ) -> RefinementInstallation:
        if not 0 <= verified_ratio <= 1:
            raise RefinementValidationError("Verified coverage ratio must be between zero and one")
        current = self._require_installation(installation_id)
        spatial_state = (
            SpatialCoverageState.COMPLETE
            if verified_ratio >= 0.995
            else SpatialCoverageState.PARTIAL
        )
        updated = replace(
            current,
            verified_geometry=verified_geometry,
            installed_at=self._clock(),
            technical_state=TechnicalResourceState.READY,
            spatial_state=spatial_state,
            file_fingerprints=tuple(file_fingerprints),
            verification_method=method,
        )
        self._repository.upsert(updated)
        return updated

    def cancel_operation(self, installation_id: str) -> RefinementInstallation:
        current = self._require_installation(installation_id)
        updated = replace(
            current,
            technical_state=TechnicalResourceState.CANCELLED,
            spatial_state=SpatialCoverageState.ABSENT,
            job_id=None,
        )
        self._repository.upsert(updated)
        return updated

    def _require_installation(self, installation_id: str) -> RefinementInstallation:
        installation = self._repository.get(installation_id)
        if installation is None:
            raise RefinementValidationError(
                f"Unknown refinement installation: {installation_id!r}"
            )
        return installation

    @staticmethod
    def _is_compatible(category_key: str, product: RefinementProduct) -> bool:
        return any(
            node == category_key or node.startswith(f"{category_key}.")
            for node in product.tlst_nodes
        )


def build_refinement_install_path(
    data_root: Path,
    *,
    category_key: str,
    provider: str,
    product: str,
    version: str,
    aoi_id: str,
) -> Path:
    return (
        data_root
        / "data"
        / "earth"
        / "refinement"
        / _safe_segment(category_key)
        / _safe_segment(provider)
        / _safe_segment(product)
        / _safe_segment(version)
        / _safe_segment(aoi_id)
    )


def _safe_segment(value: str) -> str:
    cleaned = "".join(
        character.lower() if character.isalnum() or character in {"-", "_", "."} else "-"
        for character in value.strip()
    ).strip(".-")
    if not cleaned or cleaned in {".", ".."}:
        raise RefinementValidationError("Invalid refinement storage path segment")
    return cleaned
