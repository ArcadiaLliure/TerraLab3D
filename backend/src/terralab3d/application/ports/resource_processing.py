"""Frontera de processament local per a recursos descarregats."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from terralab3d.domain.resources.models import ResourceMetadataValue


@dataclass(frozen=True, slots=True)
class ProcessedResource:
    """Asset derivat que el renderer pot consumir sense alterar la font."""

    render_path: Path
    metadata: dict[str, ResourceMetadataValue] = field(default_factory=dict)


class ResourcePostProcessor(Protocol):
    """Converteix una font instal·lada a una cache local renderitzable."""

    def process(self, source_path: Path, output_dir: Path) -> ProcessedResource: ...
