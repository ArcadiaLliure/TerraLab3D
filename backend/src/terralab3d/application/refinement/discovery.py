"""Concurrent provider discovery with revision-based stale-result rejection."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from terralab3d.application.ports.refinement import RefinementProviderPort
from terralab3d.domain.refinement.discovery import (
    DiscoveredRefinementProduct,
    DiscoveryRequest,
    DiscoveryResult,
    ProviderDiscoveryFailure,
)
from terralab3d.domain.refinement.licensing import CommercialLicensePolicy, LicenseUseStage


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

    async def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        self.cancel()
        marker = (request.request_id, request.revision)
        self._latest_request = marker
        tasks = {
            asyncio.create_task(provider.discover(request)): provider
            for provider in self._providers
        }
        self._active_tasks = set(tasks)
        candidates: list[DiscoveredRefinementProduct] = []
        failures: list[ProviderDiscoveryFailure] = []
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
        if self._latest_request != marker:
            return DiscoveryResult(request.request_id, request.revision, (), ())
        return DiscoveryResult(
            request_id=request.request_id,
            revision=request.revision,
            candidates=tuple(sorted(candidates, key=lambda item: item.candidate_id)),
            failures=tuple(failures),
        )

    def cancel(self) -> None:
        self._latest_request = None
        for task in self._active_tasks:
            task.cancel()
        self._active_tasks.clear()
