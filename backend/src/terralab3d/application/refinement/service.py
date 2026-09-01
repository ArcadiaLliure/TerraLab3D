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
    installations: tuple[RefinementInstallation, ...]


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
        import time, logging
        logger = logging.getLogger(__name__)
        t0 = time.monotonic()
        
        installations = tuple(self._repository.list_installations())
        t1 = time.monotonic()
        
        known_nodes = {
            node
            for product in self._product_catalog.list_all_products()
            for node in product.tlst_nodes
            if node in self._taxonomy.category_keys
        }
        t2 = time.monotonic()
        t3 = time.monotonic()

        state_by_key: dict[str, SpatialCoverageState] = {}
        insts_by_key: dict[str, tuple[RefinementInstallation, ...]] = {}
        ordered = sorted(
            self._taxonomy.categories,
            key=lambda item: item.key.count("."),
            reverse=True,
        )
        for category in ordered:
            cat_installations = []
            for inst in installations:
                if any(
                    n == category.key or n.startswith(f"{category.key}.") or category.key.startswith(f"{n}.")
                    for n in inst.tlst_nodes
                ):
                    cat_installations.append(inst)

            direct_states = [item.spatial_state for item in cat_installations]
            if category.key in known_nodes and not direct_states:
                direct_states.append(SpatialCoverageState.ABSENT)
            
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
            insts_by_key[category.key] = tuple(sorted(cat_installations, key=lambda i: i.installation_id))
        t4 = time.monotonic()

        nodes = tuple(
            RefinementWorkspaceNode(
                category_key=category.key,
                parent_key=category.parent_key,
                label=self._labels.get(category.key, category.key),
                state=state_by_key[category.key],
                installations=insts_by_key[category.key],
            )
            for category in self._taxonomy.categories
        )
        ws = RefinementWorkspace(
            taxonomy_key=self._taxonomy.taxonomy_key,
            taxonomy_version=self._taxonomy.taxonomy_version,
            virtual_root="surface",
            nodes=nodes,
        )
        t5 = time.monotonic()
        logger.info(f"MGP: workspace() took {t5-t0:.4f}s. list_inst: {t1-t0:.4f}s, list_prod: {t2-t1:.4f}s, dict: {t3-t2:.4f}s, agg: {t4-t3:.4f}s, build: {t5-t4:.4f}s")
        return ws

    def installations_for(
        self,
        category_key: str,
    ) -> tuple[RefinementInstallation, ...]:
        canonical = self._taxonomy.canonical_category_key(category_key)
        return tuple(
            installation
            for installation in self._repository.list_installations()
            if any(
                node == canonical
                or node.startswith(f"{canonical}.")
                or canonical.startswith(f"{node}.")
                for node in installation.tlst_nodes
            )
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
        return self.confirm_product(
            product=product,
            category_key=canonical,
            aoi_id=aoi_id,
            job_id=job_id,
        )

    def confirm_product(
        self,
        *,
        product: RefinementProduct,
        category_key: str,
        aoi_id: str,
        job_id: str,
        local_path: Path | None = None,
    ) -> RefinementInstallation:
        """Persist a queued discovered product after the second license gate."""

        canonical = self._taxonomy.canonical_category_key(category_key)
        if not self._is_compatible(canonical, product):
            raise RefinementValidationError(
                f"Product {product.product_id!r} cannot refine {canonical!r}"
            )
        self._license_policy.require_allowed(product.license, stage=LicenseUseStage.JOB_START)
        installation_id = self._id_factory()
        resolved_path = (
            local_path
            if local_path is not None
            else build_refinement_install_path(
                self._data_root,
                category_key=canonical,
                provider=product.provider,
                product=product.product,
                version=product.version,
                aoi_id=aoi_id,
            )
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
            local_path=str(resolved_path),
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

    def configurar_participacio(
        self,
        installation_id: str,
        *,
        enabled: bool,
        priority: int,
    ) -> RefinementInstallation:
        """Separa l'estat instal.lat de la participacio semantica del refinament."""

        if not isinstance(enabled, bool):
            raise RefinementValidationError("enabled ha de ser un boolean")
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise RefinementValidationError("priority ha de ser un enter")
        current = self._require_installation(installation_id)
        updated = replace(current, enabled=enabled, priority=priority)
        self._repository.upsert(updated)
        return updated

    def cancel_resource_operation(
        self,
        resource_id: str,
        variant_id: str,
    ) -> tuple[RefinementInstallation, ...]:
        """Cancel persisted refinement installations after a controller restart."""

        return tuple(
            self.cancel_operation(installation.installation_id)
            for installation in self._repository.list_installations()
            if installation.resource_id == resource_id
            and installation.variant_id == variant_id
            and installation.technical_state is not TechnicalResourceState.CANCELLED
        )

    def remove_installation(self, installation_id: str) -> RefinementInstallation:
        current = self._repository.remove(installation_id)
        if current is None:
            raise RefinementValidationError(
                f"Unknown refinement installation: {installation_id!r}"
            )
        return current

    def remove_resource_installations(
        self,
        resource_id: str,
        *,
        variant_id: str | None = None,
    ) -> tuple[RefinementInstallation, ...]:
        removed: list[RefinementInstallation] = []
        for installation in tuple(self._repository.list_installations()):
            if installation.resource_id != resource_id:
                continue
            if variant_id is not None and installation.variant_id != variant_id:
                continue
            current = self._repository.remove(installation.installation_id)
            if current is not None:
                removed.append(current)
        return tuple(removed)

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
