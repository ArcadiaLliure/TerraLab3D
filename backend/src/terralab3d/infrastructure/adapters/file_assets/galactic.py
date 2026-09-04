"""Resolució segura dels assets locals de Via Làctia i pols Planck."""

from __future__ import annotations

from pathlib import Path

from terralab3d.domain.identifiers import ResourceId, VariantId
from terralab3d.infrastructure.resources.installation_repository import (
    ResourceInstallationRepository,
)


GALACTIC_RESOURCE_IDS = frozenset(("sky.milky_way", "sky.planck_dust"))


class ManagedGalacticAssets:
    """Exposa només recursos galàctics READY registrats al repositori local."""

    def __init__(self, repository: ResourceInstallationRepository) -> None:
        self._repository = repository

    def resolve_asset(self, resource_id: str, variant_id: str | None = None) -> Path | None:
        if resource_id not in GALACTIC_RESOURCE_IDS:
            return None
        selected_variant = VariantId(variant_id) if variant_id else None
        return self._repository.resolve_render_asset(ResourceId(resource_id), selected_variant)
