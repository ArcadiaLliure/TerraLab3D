"""Concurrent provider discovery with revision-based stale-result rejection."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from typing import Any

from terralab3d.application.ports.refinement import RefinementProviderPort
from terralab3d.domain.refinement.discovery import (
    DiscoveredRefinementProduct,
    DiscoveryRequest,
    DiscoveryResult,
    ProviderDiscoveryFailure,
)
from terralab3d.domain.refinement.licensing import CommercialLicensePolicy, LicenseUseStage

logger = logging.getLogger(__name__)

class RefinementDiscoveryCoordinator:
    def __init__(
        self,
        providers: Sequence[RefinementProviderPort],
        license_policy: CommercialLicensePolicy,
    ) -> None:
        self._providers = tuple(providers)
        self._license_policy = license_policy
        self._latest_request: tuple[str, int] | None = None
        self._active_tasks: set[
            asyncio.Task[Sequence[DiscoveredRefinementProduct]]
        ] = set()
        self._spatial_cache: dict[str, tuple[list[DiscoveredRefinementProduct], Any]] = {}

    async def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        logger.info("MGP: Refinement discovery STARTED for request %s (rev %d)", request.request_id, request.revision)
        self.cancel()
        marker = (request.request_id, request.revision)
        self._latest_request = marker
        
        import dataclasses
        from shapely.geometry import shape, mapping
        
        aoi = shape(dict(request.aoi_geojson))
        cached_candidates, searched_aoi = self._spatial_cache.get(request.category_key, ([], None))
        
        unsearched = aoi.difference(searched_aoi) if searched_aoi is not None else aoi
        
        candidates: list[DiscoveredRefinementProduct] = []
        failures: list[ProviderDiscoveryFailure] = []
        
        if not unsearched.is_empty:
            search_request = dataclasses.replace(request, aoi_geojson=mapping(unsearched))
            tasks = {
                asyncio.create_task(provider.discover(search_request)): provider
                for provider in self._providers
            }
            self._active_tasks = set(tasks)
            
            for task, provider in tasks.items():
                try:
                    values = await task
                    if self._latest_request != marker:
                        continue
                    for candidate in values:
                        decision = self._license_policy.evaluate(
                            candidate.license,
                            stage=LicenseUseStage.CATALOG_DISPLAY,
                        )
                        if decision.allowed:
                            candidates.append(candidate)
                        else:
                            failures.append(
                                ProviderDiscoveryFailure(
                                    provider_id=str(provider.provider_id),
                                    code=decision.code.value,
                                    message=decision.reason,
                                )
                            )
                except asyncio.CancelledError:
                    continue
                except Exception as exc:
                    failures.append(
                        ProviderDiscoveryFailure(
                            provider_id=str(provider.provider_id),
                            code="provider_error",
                            message=str(exc),
                        )
                    )
                finally:
                    self._active_tasks.discard(task)
                    
            if self._latest_request == marker:
                # Deduplicate and add to cache
                existing_ids = {c.candidate_id for c in cached_candidates}
                for c in candidates:
                    if c.candidate_id not in existing_ids:
                        cached_candidates.append(c)
                        existing_ids.add(c.candidate_id)
                self._spatial_cache[request.category_key] = (
                    cached_candidates,
                    aoi.union(searched_aoi) if searched_aoi is not None else aoi
                )
                
        if self._latest_request != marker:
            return DiscoveryResult(request.request_id, request.revision, (), ())
            
        # Filter all cached candidates by current AOI intersection
        final_candidates = [
            c for c in cached_candidates
            if shape(dict(c.footprint)).intersects(aoi)
        ]
        
        logger.info("MGP: Refinement discovery COMPLETED for request %s (rev %d)", request.request_id, request.revision)
        return DiscoveryResult(
            request_id=request.request_id,
            revision=request.revision,
            candidates=tuple(sorted(final_candidates, key=lambda item: (item.resolution_m, item.candidate_id))),
            failures=tuple(failures),
        )

    def cancel(self) -> None:
        self._latest_request = None
        for task in self._active_tasks:
            task.cancel()
        self._active_tasks.clear()
