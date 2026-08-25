"""WebSocket-facing orchestration for the TLST refinement vertical."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
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


class RefinementBridgeController:
    """Keep request revisions, provider I/O and jobs outside the bridge itself."""

    _METRIC_CRS = "EPSG:3035"

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

    def remove_installation(self, message: Mapping[str, object]) -> None:
        asyncio.create_task(self._remove_installation(message))

    async def _publish_workspace(self, message: Mapping[str, object]) -> None:
        request_id, revision = _request_marker(message)
        aoi = _optional_geometry(message.get("aoi"))
        try:
            workspace = await asyncio.to_thread(self._service.workspace)
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
                                "installationIds": list(node.installation_ids),
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
            candidate_payloads = await asyncio.to_thread(
                self._candidate_payloads,
                session,
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
    ) -> list[dict[str, object]]:
        aoi, local, products = self._coverage_inputs(session)
        contributions = {
            item.product_id: item
            for item in evaluate_product_contributions(
                aoi,
                local,
                products,
                self._geometry,
            )
        }
        return [
            self._candidate_payload(
                candidate,
                contributions[candidate.candidate_id].available_ratio * 100,
                contributions[candidate.candidate_id].new_effective_ratio * 100,
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
            plan, coverage_payload = await asyncio.to_thread(
                self._build_plan,
                session,
                product_ids,
                plan_id,
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
    ) -> tuple[ParametricDownloadPlan, dict[str, object]]:
        plan = freeze_parametric_plan(
            session.request,
            session.result.candidates,
            product_ids,
            self._license_policy,
            plan_id=plan_id,
            processing_options={"extractArchives": True},
        )
        aoi, local, all_products = self._coverage_inputs(session)
        selected = tuple(
            product.geometry
            for product in all_products
            if product.product_id in plan.product_ids
        )
        coverage = calculate_coverage(aoi, local, selected, self._geometry)
        recommendation = greedy_coverage_plan(
            aoi,
            local,
            all_products,
            self._geometry,
        )
        return plan, {
            "existingPercent": coverage.existing_ratio * 100,
            "newEffectivePercent": coverage.new_effective_ratio * 100,
            "plannedPercent": coverage.planned_ratio * 100,
            "remainingPercent": coverage.remaining_ratio * 100,
            "existing": self._geometry.to_geojson(
                coverage.existing, target_crs="EPSG:4326"
            ),
            "planned": self._geometry.to_geojson(
                coverage.planned, target_crs="EPSG:4326"
            ),
            "remaining": self._geometry.to_geojson(
                coverage.remaining_gap, target_crs="EPSG:4326"
            ),
            "recommendedProductIds": list(recommendation.selected_product_ids),
        }

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
            descriptor = resource_descriptor_from_plan(plan)
            self._resource_catalog.upsert(descriptor)
            variant = descriptor.variants[0]
            expected_job_id = f"{descriptor.id}_{variant.id}"
            install_path = (
                self._data_root
                / "data"
                / "earth"
                / "surface"
                / "refinements"
                / descriptor.id.rsplit(".", 1)[-1]
            )
            installation_ids: list[str] = []
            for candidate in planned.candidates:
                product = RefinementProduct(
                    product_id=candidate.candidate_id,
                    resource_id=str(descriptor.id),
                    variant_id=str(variant.id),
                    provider=candidate.provider,
                    product=candidate.product,
                    version=candidate.version,
                    tlst_nodes=candidate.compatible_tlst_nodes,
                    data_kind=(
                        RefinementDataKind.VECTOR
                        if any(asset.class_attribute for asset in candidate.assets)
                        else RefinementDataKind.RASTER
                    ),
                    original_crs="EPSG:4326",
                    planned_geometry=GeometryRecord(
                        "EPSG:4326", candidate.footprint
                    ),
                    license=candidate.license,
                    provenance_url=candidate.license.provenance_url,
                )
                installation = self._service.confirm_product(
                    product=product,
                    category_key=plan.category_keys[0],
                    aoi_id=plan.plan_id,
                    job_id=expected_job_id,
                    local_path=install_path,
                )
                installation_ids.append(installation.installation_id)
            if self._processor_factory is not None:
                processor = self._processor_factory.build(
                    plan,
                    planned.candidates,
                    tuple(installation_ids),
                )
                self._download_jobs.register_post_processor(descriptor.id, processor)
            job_id = self._download_jobs.start_download(descriptor.id, variant.id)
            if job_id != expected_job_id:
                raise RefinementValidationError("Download manager returned an unexpected job id")
            await self._publisher.send(
                {
                    "type": "refinement_download_progress",
                    "requestId": request_id,
                    "revision": revision,
                    "planId": plan.plan_id,
                    "jobId": job_id,
                    "state": TechnicalResourceState.QUEUED.value,
                    "downloadedBytes": 0,
                    "totalBytes": plan.estimated_bytes,
                    "progress": 0.0,
                    "currentFile": None,
                    "outputs": _empty_outputs(),
                    "error": None,
                }
            )
        except Exception as exc:
            await self._send_error(request_id, revision, "confirm", exc)

    async def _remove_installation(self, message: Mapping[str, object]) -> None:
        request_id, revision = _request_marker(message)
        try:
            installation_id = _required_string(message, "installationId")
            installation = await asyncio.to_thread(
                self._service.remove_installation,
                installation_id,
            )
            self._download_jobs.delete_resource(
                ResourceId(installation.resource_id),
                VariantId(installation.variant_id),
            )
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
        }

    def _require_discovery(self, request_id: str, revision: int) -> _DiscoverySession:
        session = self._discoveries.get((request_id, revision))
        if session is None:
            raise RefinementValidationError("Unknown or stale discovery result")
        return session

    async def _send_error(
        self,
        request_id: str,
        revision: int,
        operation: str,
        error: Exception,
    ) -> None:
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
