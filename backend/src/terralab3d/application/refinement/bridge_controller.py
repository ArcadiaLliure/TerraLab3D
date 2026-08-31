"""WebSocket-facing orchestration for the TLST refinement vertical."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from terralab3d.application.ports.refinement import GeometryPort
from terralab3d.application.ports.resource_processing import ResourcePostProcessor
from terralab3d.application.refinement.discovery import RefinementDiscoveryCoordinator
from terralab3d.application.refinement.downloads import (
    asset_file_name,
    freeze_parametric_plan,
    refinement_resource_id,
    resource_descriptor_from_plan,
)
from terralab3d.application.refinement.service import RefinementService
from terralab3d.domain.identifiers import ResourceId, VariantId
from terralab3d.domain.refinement.coverage import (
    MetricGeometry,
    ProductFootprint,
    calculate_coverage,
    evaluate_product_contributions,
    greedy_coverage_plan,
)
from terralab3d.domain.refinement.discovery import (
    DiscoveredRefinementProduct,
    DiscoveryRequest,
    DiscoveryResult,
)
from terralab3d.domain.refinement.downloads import ParametricDownloadPlan
from terralab3d.domain.refinement.errors import RefinementError, RefinementValidationError
from terralab3d.domain.refinement.installations import (
    GeometryRecord,
    RefinementDataKind,
    RefinementProduct,
    TechnicalResourceState,
)
from terralab3d.domain.refinement.licensing import CommercialLicensePolicy
from terralab3d.domain.refinement.states import SpatialCoverageState
from terralab3d.domain.resources.models import ResourceDescriptor


class RefinementPublisher(Protocol):
    async def send(self, msg: dict[str, object]) -> None: ...


class RefinementResourceCatalog(Protocol):
    def upsert(self, descriptor: ResourceDescriptor) -> None: ...


class RefinementDownloadJobs(Protocol):
    def start_download(self, resource_id: ResourceId, variant_id: VariantId) -> str: ...

    def delete_resource(self, resource_id: ResourceId, variant_id: VariantId) -> None: ...

    def cancel_download(self, resource_id: ResourceId, variant_id: VariantId) -> None: ...

    def register_post_processor(
        self,
        resource_id: ResourceId,
        processor: ResourcePostProcessor,
    ) -> None: ...


class RefinementProcessorFactory(Protocol):
    def build(
        self,
        plan: ParametricDownloadPlan,
        candidates: tuple[DiscoveredRefinementProduct, ...],
        installation_ids: tuple[str, ...],
    ) -> ResourcePostProcessor: ...


@dataclass(frozen=True, slots=True)
class _DiscoverySession:
    request: DiscoveryRequest
    result: DiscoveryResult


@dataclass(frozen=True, slots=True)
class _PlannedSession:
    plan: ParametricDownloadPlan
    candidates: tuple[DiscoveredRefinementProduct, ...]


@dataclass(frozen=True, slots=True)
class _ActiveDownload:
    request_id: str
    revision: int
    plan_id: str
    job_id: str
    resource_id: ResourceId
    variant_id: VariantId
    installation_ids: tuple[str, ...]
    total_bytes: int | None


class RefinementBridgeController:
    """Keep request revisions, provider I/O and jobs outside the bridge itself."""

    _METRIC_CRS = "EPSG:3035"
    # A greedy set cover recalculates a geometric gain for every remaining tile.
    # It is useful as an interactive hint for a small catalogue, but becomes an
    # O(n²) operation for tiled products and must never hold up a confirmed plan.
    _MAX_EXHAUSTIVE_RECOMMENDATION_CANDIDATES = 512

    def __init__(
        self,
        *,
        publisher: RefinementPublisher,
        discovery: RefinementDiscoveryCoordinator,
        service: RefinementService,
        geometry: GeometryPort,
        license_policy: CommercialLicensePolicy,
        resource_catalog: RefinementResourceCatalog,
        download_jobs: RefinementDownloadJobs,
        data_root: Path,
        processor_factory: RefinementProcessorFactory | None = None,
    ) -> None:
        self._publisher = publisher
        self._discovery = discovery
        self._service = service
        self._geometry = geometry
        self._license_policy = license_policy
        self._resource_catalog = resource_catalog
        self._download_jobs = download_jobs
        self._data_root = data_root
        self._processor_factory = processor_factory
        self._query_task: asyncio.Task[None] | None = None
        self._discoveries: dict[tuple[str, int], _DiscoverySession] = {}
        self._plans: dict[str, _PlannedSession] = {}
        self._active_downloads: dict[str, _ActiveDownload] = {}

    def request_workspace(self, message: Mapping[str, object]) -> None:
        asyncio.create_task(self._publish_workspace(message))

    def query_products(self, message: Mapping[str, object]) -> None:
        self.cancel_query(message)
        self._query_task = asyncio.create_task(self._query_products(message))

    def cancel_query(self, _message: Mapping[str, object]) -> None:
        self._discovery.cancel()
        if self._query_task is not None:
            self._query_task.cancel()
            self._query_task = None

    def calculate_plan(self, message: Mapping[str, object]) -> None:
        asyncio.create_task(self._calculate_plan(message))

    def confirm_download(self, message: Mapping[str, object]) -> None:
        asyncio.create_task(self._confirm_download(message))

    def cancel_download(self, message: Mapping[str, object]) -> None:
        asyncio.create_task(self._cancel_download(message))

    def remove_installation(self, message: Mapping[str, object]) -> None:
        asyncio.create_task(self._remove_installation(message))

    async def _publish_workspace(self, message: Mapping[str, object]) -> None:
        request_id, revision = _request_marker(message)
        import logging
        logging.getLogger(__name__).info(f"MGP: _publish_workspace receiving request_id={request_id}, revision={revision}")
        aoi = _optional_geometry(message.get("aoi"))
        
        import shapely.geometry
        aoi_shape = shapely.geometry.shape(aoi) if aoi else None
        
        def get_footprint(inst):
            if aoi_shape is None:
                return None
            fp = dict(inst.verified_geometry.geojson) if inst.verified_geometry else dict(inst.planned_geometry.geojson)
            try:
                if aoi_shape.intersects(shapely.geometry.shape(fp)):
                    return fp
            except Exception:
                pass
            return None

        try:
            workspace = await asyncio.to_thread(self._service.workspace)
            logging.getLogger(__name__).info(f"MGP: _publish_workspace sending response request_id={request_id}, revision={revision}")
            await self._publisher.send(
                {
                    "type": "refinement_workspace_snapshot",
                    "requestId": request_id,
                    "revision": revision,
                    "workspace": {
                        "taxonomyKey": workspace.taxonomy_key,
                        "taxonomyVersion": workspace.taxonomy_version,
                        "virtualRoot": workspace.virtual_root,
                        "aoi": aoi,
                        "nodes": [
                            {
                                "categoryKey": node.category_key,
                                "parentKey": node.parent_key,
                                "label": node.label,
                                "depth": node.category_key.count("."),
                                "state": node.state.value,
                                "verifiedPercent": (
                                    100.0
                                    if node.state is SpatialCoverageState.COMPLETE
                                    else 0.0
                                ),
                                "plannedPercent": (
                                    100.0
                                    if node.state is SpatialCoverageState.COMPLETE
                                    else 0.0
                                ),
                                "installations": [
                                    {
                                        "installationId": inst.installation_id,
                                        "provider": inst.provider,
                                        "product": inst.product,
                                        "version": inst.version,
                                        "footprint": get_footprint(inst),
                                    }
                                    for inst in node.installations
                                ],
                                "applicable": (
                                    node.state is not SpatialCoverageState.NOT_APPLICABLE
                                ),
                            }
                            for node in workspace.nodes
                        ],
                    },
                }
            )
        except Exception as exc:
            await self._send_error(request_id, revision, "workspace", exc)

    async def _query_products(self, message: Mapping[str, object]) -> None:
        request_id, revision = _request_marker(message)
        try:
            request = DiscoveryRequest(
                request_id=request_id,
                revision=revision,
                category_key=_required_string(message, "categoryKey"),
                aoi_geojson=_required_geometry(message, "aoi"),
            )
            result = await self._discovery.discover(request)
            session = _DiscoverySession(request, result)
            self._discoveries[(request_id, revision)] = session
            loop = asyncio.get_running_loop()

            def report_progress(fraction: float, message: str) -> None:
                async def _send() -> None:
                    await self._publisher.send({
                        "type": "refinement_operation_progress",
                        "requestId": request_id,
                        "revision": revision,
                        "operation": "query",
                        "progressFraction": fraction,
                        "message": message,
                    })
                asyncio.run_coroutine_threadsafe(_send(), loop)

            candidate_payloads = await asyncio.to_thread(
                self._candidate_payloads,
                session,
                report_progress,
            )
            await self._publisher.send(
                {
                    "type": "refinement_candidates",
                    "requestId": request_id,
                    "revision": revision,
                    "categoryKey": request.category_key,
                    "candidates": candidate_payloads,
                    "failures": [
                        {
                            "providerId": failure.provider_id,
                            "code": failure.code,
                            "message": failure.message,
                        }
                        for failure in result.failures
                    ],
                }
            )
        except asyncio.CancelledError:
            return
        except Exception as exc:
            await self._send_error(request_id, revision, "query", exc)

    def _candidate_payloads(
        self,
        session: _DiscoverySession,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> list[dict[str, object]]:
        import logging
        import time
        t0 = time.monotonic()
        if progress_callback:
            progress_callback(0.0, "Preparant petjades...")
        aoi, local, products = self._coverage_inputs(session)
        t1 = time.monotonic()
        logging.getLogger(__name__).info(f"MGP: _coverage_inputs took {t1-t0:.4f}s for {len(products)} products")
        contributions = {
            item.product_id: item
            for item in evaluate_product_contributions(
                aoi,
                local,
                products,
                self._geometry,
                progress_callback=progress_callback,
            )
        }
        workspace_installations = self._service.installations_for(session.request.category_key)

        def find_installation_id(candidate: DiscoveredRefinementProduct) -> str | None:
            for inst in workspace_installations:
                if (
                    inst.provider == candidate.provider
                    and inst.product == candidate.product
                    and inst.version == candidate.version
                ):
                    return inst.installation_id
            return None

        return [
            self._candidate_payload(
                candidate,
                contributions[candidate.candidate_id].available_ratio * 100,
                contributions[candidate.candidate_id].new_effective_ratio * 100,
                find_installation_id(candidate),
            )
            for candidate in session.result.candidates
        ]

    async def _calculate_plan(self, message: Mapping[str, object]) -> None:
        request_id, revision = _request_marker(message)
        try:
            session = self._require_discovery(request_id, revision)
            category_key = _required_string(message, "categoryKey")
            aoi = _required_geometry(message, "aoi")
            product_ids = _required_string_list(message, "productIds")
            if category_key != session.request.category_key or not _same_json(
                aoi, session.request.aoi_geojson
            ):
                raise RefinementValidationError("The discovery request is stale")
            plan_id = f"{request_id}-r{revision}-{uuid4().hex[:8]}"

            loop = asyncio.get_running_loop()
            def report_progress(fraction: float, message: str) -> None:
                async def _send() -> None:
                    await self._publisher.send({
                        "type": "refinement_operation_progress",
                        "requestId": request_id,
                        "revision": revision,
                        "operation": "plan",
                        "progressFraction": fraction,
                        "message": message,
                    })
                asyncio.run_coroutine_threadsafe(_send(), loop)

            plan, coverage_payload = await asyncio.to_thread(
                self._build_plan,
                session,
                product_ids,
                plan_id,
                report_progress,
            )
            selected = tuple(
                candidate
                for candidate in session.result.candidates
                if candidate.candidate_id in plan.product_ids
            )
            self._plans[plan.plan_id] = _PlannedSession(plan, selected)
            await self._publisher.send(
                {
                    "type": "refinement_plan_summary",
                    "requestId": request_id,
                    "revision": revision,
                    "categoryKey": category_key,
                    "productIds": list(plan.product_ids),
                    "coverage": coverage_payload,
                    "plan": plan.to_dict(),
                }
            )
        except Exception as exc:
            await self._send_error(request_id, revision, "plan", exc)

    def _build_plan(
        self,
        session: _DiscoverySession,
        product_ids: Sequence[str],
        plan_id: str,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> tuple[ParametricDownloadPlan, dict[str, object]]:
        plan = freeze_parametric_plan(
            session.request,
            session.result.candidates,
            product_ids,
            self._license_policy,
            plan_id=plan_id,
            processing_options={"extractArchives": True},
        )
        if progress_callback:
            progress_callback(0.02, "Preparant geometries de cobertura…")
        aoi, local, all_products = self._coverage_inputs(session)
        selected = tuple(
            product.geometry
            for product in all_products
            if product.product_id in plan.product_ids
        )
        if progress_callback:
            progress_callback(
                0.12,
                f"Calculant cobertura del pla seleccionat ({len(selected):,} tessel·les)…",
            )
        coverage = calculate_coverage(aoi, local, selected, self._geometry)
        recommended_product_ids: tuple[str, ...] = ()
        if self._should_calculate_exhaustive_recommendation(len(all_products)):
            if progress_callback:
                progress_callback(0.72, "Calculant mosaic recomanat…")
            recommendation = greedy_coverage_plan(
                aoi,
                local,
                all_products,
                self._geometry,
                progress_callback=progress_callback,
            )
            recommended_product_ids = recommendation.selected_product_ids
        elif progress_callback:
            progress_callback(
                0.78,
                "Mosaic recomanat omès: el catàleg és massa gran per calcular-lo exhaustivament.",
            )
        if progress_callback:
            progress_callback(0.90, "Preparant geometries per visualitzar…")
        return plan, {
            "existingPercent": coverage.existing_ratio * 100,
            "newEffectivePercent": coverage.new_effective_ratio * 100,
            "plannedPercent": coverage.planned_ratio * 100,
            "remainingPercent": coverage.remaining_ratio * 100,
            "existing": self._geometry.to_geojson(
                self._geometry.simplify_for_visualization(coverage.existing), target_crs="EPSG:4326"
            ),
            "planned": self._geometry.to_geojson(
                self._geometry.simplify_for_visualization(coverage.planned), target_crs="EPSG:4326"
            ),
            "remaining": self._geometry.to_geojson(
                self._geometry.simplify_for_visualization(coverage.remaining_gap), target_crs="EPSG:4326"
            ),
            "recommendedProductIds": list(recommended_product_ids),
        }

    @classmethod
    def _should_calculate_exhaustive_recommendation(cls, candidate_count: int) -> bool:
        return candidate_count <= cls._MAX_EXHAUSTIVE_RECOMMENDATION_CANDIDATES

    async def _confirm_download(self, message: Mapping[str, object]) -> None:
        request_id, revision = _request_marker(message)
        try:
            plan_id = _required_string(message, "planId")
            planned = self._plans.get(plan_id)
            if (
                planned is None
                or planned.plan.request_id != request_id
                or planned.plan.revision != revision
            ):
                raise RefinementValidationError("Unknown or stale refinement plan")
            confirmed = message.get("largeDownloadConfirmed") is True
            if planned.plan.requires_large_download_confirmation and not confirmed:
                raise RefinementValidationError(
                    "Large download confirmation is required"
                )
            options = dict(planned.plan.processing_options)
            options["largeDownloadConfirmed"] = confirmed
            plan = replace(planned.plan, processing_options=options)
            await self._send_confirm_progress(
                request_id,
                revision,
                f"Preparant el pla local de {len(plan.assets)} fitxers…",
            )
            descriptor = await asyncio.to_thread(resource_descriptor_from_plan, plan)
            variant = descriptor.variants[0]
            expected_job_id = f"{descriptor.id}_{variant.id}"
            await self._send_confirm_progress(
                request_id,
                revision,
                "Registrant el pla al catàleg local…",
            )
            await asyncio.to_thread(self._resource_catalog.upsert, descriptor)
            install_path = (
                self._data_root
                / "data"
                / "earth"
                / "surface"
                / "refinements"
                / descriptor.id.rsplit(".", 1)[-1]
            )
            installation_ids: list[str] = []
            installation_products = self._installation_products(
                plan,
                planned.candidates,
                resource_id=str(descriptor.id),
                variant_id=str(variant.id),
            )
            for index, product in enumerate(installation_products, start=1):
                await self._send_confirm_progress(
                    request_id,
                    revision,
                    (
                        "Registrant datasets locals "
                        f"({index}/{len(installation_products)}): {product.product}…"
                    ),
                )
                installation = await asyncio.to_thread(
                    self._service.confirm_product,
                    product=product,
                    category_key=plan.category_keys[0],
                    aoi_id=plan.plan_id,
                    job_id=expected_job_id,
                    local_path=install_path,
                )
                installation_ids.append(installation.installation_id)
            if self._processor_factory is not None:
                await self._send_confirm_progress(
                    request_id,
                    revision,
                    "Preparant el refinament posterior a la descàrrega…",
                )
                processor = self._processor_factory.build(
                    plan,
                    planned.candidates,
                    tuple(installation_ids),
                )
                self._download_jobs.register_post_processor(descriptor.id, processor)
            self._active_downloads[plan.plan_id] = _ActiveDownload(
                request_id=request_id,
                revision=revision,
                plan_id=plan.plan_id,
                job_id=expected_job_id,
                resource_id=descriptor.id,
                variant_id=variant.id,
                installation_ids=tuple(installation_ids),
                total_bytes=plan.estimated_bytes,
            )
            await self._publisher.send(
                {
                    "type": "refinement_download_progress",
                    "requestId": request_id,
                    "revision": revision,
                    "planId": plan.plan_id,
                    "jobId": expected_job_id,
                    "state": TechnicalResourceState.QUEUED.value,
                    "downloadedBytes": 0,
                    "totalBytes": plan.estimated_bytes,
                    "progress": 0.0 if plan.estimated_bytes is not None else None,
                    "currentFile": None,
                    "assetProgress": [],
                    "outputs": _empty_outputs(),
                    "error": None,
                }
            )
            job_id = self._download_jobs.start_download(descriptor.id, variant.id)
            if job_id != expected_job_id:
                self._active_downloads.pop(plan.plan_id, None)
                raise RefinementValidationError(
                    "Download manager returned an unexpected job id"
                )
        except Exception as exc:
            await self._send_error(request_id, revision, "confirm", exc)

    @staticmethod
    def _installation_products(
        plan: ParametricDownloadPlan,
        candidates: tuple[DiscoveredRefinementProduct, ...],
        *,
        resource_id: str,
        variant_id: str,
    ) -> tuple[RefinementProduct, ...]:
        """Create one persistent installation per dataset, never per remote tile."""

        grouped: dict[
            tuple[str, str, str],
            list[DiscoveredRefinementProduct],
        ] = {}
        for candidate in candidates:
            key = (
                candidate.provider_id,
                candidate.dataset_identifier,
                candidate.version,
            )
            grouped.setdefault(key, []).append(candidate)

        products: list[RefinementProduct] = []
        for group in grouped.values():
            first = group[0]
            tlst_nodes = tuple(
                dict.fromkeys(
                    node
                    for candidate in group
                    for node in candidate.compatible_tlst_nodes
                )
            )
            products.append(
                RefinementProduct(
                    product_id=first.dataset_identifier,
                    resource_id=resource_id,
                    variant_id=variant_id,
                    provider=first.provider,
                    product=first.product,
                    version=first.version,
                    tlst_nodes=tlst_nodes,
                    data_kind=(
                        RefinementDataKind.VECTOR
                        if any(
                            asset.class_attribute
                            for candidate in group
                            for asset in candidate.assets
                        )
                        else RefinementDataKind.RASTER
                    ),
                    original_crs="EPSG:4326",
                    planned_geometry=GeometryRecord("EPSG:4326", plan.aoi_geojson),
                    license=first.license,
                    provenance_url=first.license.provenance_url,
                )
            )
        return tuple(products)

    async def _cancel_download(self, message: Mapping[str, object]) -> None:
        request_id, revision = _request_marker(message)
        try:
            plan_id = _required_string(message, "planId")
            active = self._active_downloads.get(plan_id)
            if active is not None and (
                active.request_id != request_id or active.revision != revision
            ):
                raise RefinementValidationError("Unknown or stale active refinement download")
            resource_id = active.resource_id if active is not None else refinement_resource_id(plan_id)
            variant_id = active.variant_id if active is not None else VariantId(f"plan-r{revision}")
            job_id = active.job_id if active is not None else f"{resource_id}_{variant_id}"
            total_bytes = active.total_bytes if active is not None else None
            self._download_jobs.cancel_download(resource_id, variant_id)
            if active is not None:
                for installation_id in active.installation_ids:
                    self._service.cancel_operation(installation_id)
                self._active_downloads.pop(plan_id, None)
            else:
                await asyncio.to_thread(
                    self._service.cancel_resource_operation,
                    str(resource_id),
                    str(variant_id),
                )
            await self._publisher.send(
                {
                    "type": "refinement_download_progress",
                    "requestId": request_id,
                    "revision": revision,
                    "planId": plan_id,
                    "jobId": job_id,
                    "state": TechnicalResourceState.CANCELLED.value,
                    "downloadedBytes": 0,
                    "totalBytes": total_bytes,
                    "progress": None,
                    "currentFile": None,
                    "assetProgress": [],
                    "outputs": _empty_outputs(),
                    "error": None,
                }
            )
        except Exception as exc:
            await self._send_error(request_id, revision, "cancel", exc)

    async def _remove_installation(self, message: Mapping[str, object]) -> None:
        request_id, revision = _request_marker(message)
        try:
            installation_id = _required_string(message, "installationId")
            installation = await asyncio.to_thread(
                self._service.remove_installation,
                installation_id,
            )
            
            all_insts = await asyncio.to_thread(self._service._repository.list_installations)
            still_used = any(i.resource_id == installation.resource_id for i in all_insts)
            
            if not still_used:
                self._download_jobs.delete_resource(
                    ResourceId(installation.resource_id),
                    VariantId(installation.variant_id),
                )
                from terralab3d.infrastructure.app_paths import resolve_resource_install_dir
                import shutil
                final_dir = resolve_resource_install_dir(installation.resource_id)
                if final_dir.exists():
                    shutil.rmtree(final_dir, ignore_errors=True)

            await self._publisher.send(
                {
                    "type": "refinement_installation_removed",
                    "requestId": request_id,
                    "revision": revision,
                    "installationId": installation_id,
                }
            )
        except Exception as exc:
            await self._send_error(request_id, revision, "remove", exc)

    def _coverage_inputs(
        self,
        session: _DiscoverySession,
    ) -> tuple[
        MetricGeometry,
        tuple[MetricGeometry, ...],
        tuple[ProductFootprint, ...],
    ]:
        aoi = self._geometry.from_geojson(
            session.request.aoi_geojson,
            source_crs="EPSG:4326",
            target_crs=self._METRIC_CRS,
        )
        workspace_installations = self._service.installations_for(
            session.request.category_key
        )
        local = tuple(
            self._geometry.from_geojson(
                installation.verified_geometry.geojson,
                source_crs=installation.verified_geometry.crs,
                target_crs=self._METRIC_CRS,
            )
            for installation in workspace_installations
            if installation.verified_geometry is not None
            and installation.technical_state is TechnicalResourceState.READY
        )
        products = tuple(
            ProductFootprint(
                candidate.candidate_id,
                self._geometry.from_geojson(
                    candidate.footprint,
                    source_crs="EPSG:4326",
                    target_crs=self._METRIC_CRS,
                ),
            )
            for candidate in session.result.candidates
        )
        return aoi, local, products

    @staticmethod
    def _candidate_payload(
        candidate: DiscoveredRefinementProduct,
        available_percent: float,
        new_effective_percent: float,
        installation_id: str | None,
    ) -> dict[str, object]:
        return {
            "candidateId": candidate.candidate_id,
            "providerId": candidate.provider_id,
            "provider": candidate.provider,
            "product": candidate.product,
            "version": candidate.version,
            "datasetIdentifier": candidate.dataset_identifier,
            "compatibleTlstNodes": list(candidate.compatible_tlst_nodes),
            "footprint": dict(candidate.footprint),
            "resolutionM": candidate.resolution_m,
            "temporalStart": candidate.temporal_start,
            "temporalEnd": candidate.temporal_end,
            "format": candidate.format,
            "estimatedBytes": candidate.estimated_bytes,
            "availablePercent": available_percent,
            "newEffectivePercent": new_effective_percent,
            "qualifierKey": candidate.qualifier_key,
            "endpointVerified": candidate.endpoint_verified,
            "license": {
                "licenseId": candidate.license.license_id,
                "officialUrl": candidate.license.official_url,
                "attribution": candidate.license.attribution_text,
                "commercialUse": True,
                "checkedAt": candidate.license.checked_at.isoformat()
                if candidate.license.checked_at
                else "",
            },
            "assets": [
                {
                    "assetId": asset.asset_id,
                    "fileName": asset_file_name(
                        asset.s3_path, asset.download_url, asset.asset_id
                    ),
                    "footprint": dict(asset.footprint),
                    "order": asset.order,
                    "estimatedBytes": asset.estimated_bytes,
                    "checksumAlgorithm": asset.checksum_algorithm,
                    "checksumValue": asset.checksum_value,
                    "requiresAuthentication": asset.requires_authentication,
                    "classAttribute": asset.class_attribute,
                }
                for asset in candidate.assets
            ],
            "installationId": installation_id,
        }

    def _require_discovery(self, request_id: str, revision: int) -> _DiscoverySession:
        session = self._discoveries.get((request_id, revision))
        if session is None:
            import logging
            keys = list(self._discoveries.keys())
            logging.getLogger(__name__).error(f"MGP: _require_discovery failed for {request_id} rev {revision}. Available keys: {keys}")
            raise RefinementValidationError("Unknown or stale discovery result")
        return session

    async def _send_confirm_progress(
        self,
        request_id: str,
        revision: int,
        message: str,
    ) -> None:
        await self._publisher.send(
            {
                "type": "refinement_operation_progress",
                "requestId": request_id,
                "revision": revision,
                "operation": "confirm",
                "progressFraction": 0.0,
                "message": message,
            }
        )

    async def _send_error(
        self,
        request_id: str,
        revision: int,
        operation: str,
        error: Exception,
    ) -> None:
        import logging
        logging.getLogger(__name__).error(f"MGP: Refinement operation '{operation}' failed for request {request_id} rev {revision}: {error}", exc_info=error)
        code = "validation_error" if isinstance(error, RefinementError) else "internal_error"
        await self._publisher.send(
            {
                "type": "refinement_operation_error",
                "requestId": request_id,
                "revision": revision,
                "operation": operation,
                "code": code,
                "message": str(error),
            }
        )


def _request_marker(message: Mapping[str, object]) -> tuple[str, int]:
    return _required_string(message, "requestId"), _required_int(message, "revision")


def _required_string(message: Mapping[str, object], key: str) -> str:
    value = message.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RefinementValidationError(f"{key} must be a non-empty string")
    return value


def _required_int(message: Mapping[str, object], key: str) -> int:
    value = message.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise RefinementValidationError(f"{key} must be a non-negative integer")
    return value


def _required_geometry(message: Mapping[str, object], key: str) -> dict[str, object]:
    value = message.get(key)
    geometry = _optional_geometry(value)
    if geometry is None:
        raise RefinementValidationError(f"{key} must be Polygon or MultiPolygon GeoJSON")
    return geometry


def _optional_geometry(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or value.get("type") not in {"Polygon", "MultiPolygon"}:
        raise RefinementValidationError("AOI must be Polygon or MultiPolygon GeoJSON")
    return {str(key): item for key, item in value.items()}


def _required_string_list(message: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = message.get(key)
    if not isinstance(value, list) or not value or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise RefinementValidationError(f"{key} must be a non-empty string array")
    return tuple(dict.fromkeys(value))


def _same_json(left: Mapping[str, object], right: Mapping[str, object]) -> bool:
    return json.dumps(left, sort_keys=True) == json.dumps(dict(right), sort_keys=True)


def _empty_outputs() -> dict[str, None]:
    return {
        "manifest": None,
        "mosaic": None,
        "source": None,
        "quality": None,
        "conflict": None,
    }
