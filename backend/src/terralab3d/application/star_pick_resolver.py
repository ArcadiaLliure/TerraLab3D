"""Resolutor de picks estel·lars O(1) per índex.

Responsabilitats:
- Mantenir una taula de pick per cada recurs estel·lar resident
- Resoldre (resource_id, version, catalog_index) → dades científiques
- Validar resource, versió, index, dades finites
- source_id preservat com int64

Lifecycle:
  resource registered → pick table valid
  resource replaced → old version stale
  resource evicted → pick table removed
  shutdown → all removed
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from terralab3d.domain.stars.models import StarBatch
from terralab3d.domain.stars.star_pick_models import (
    ResolvedStarPick,
    StarPickRequest,
    StarPickResponse,
)

log = logging.getLogger("terralab3d.stars.picker")


@dataclass(frozen=True, slots=True)
class StarPickTable:
    """Taula de pick per a un recurs estel·lar resident.

    Referència directa al StarBatch immutable — sense còpies.
    """
    resource_id: str
    version: str
    role: str
    batch: StarBatch  # referència, no còpia — StarBatch és immutable


class StarPickResolver:
    """Resolutor O(1) de picks estel·lars per índex."""

    def __init__(self) -> None:
        self._tables: dict[str, StarPickTable] = {}
        self._disposed = False

    def register(
        self,
        resource_id: str,
        version: str,
        role: str,
        batch: StarBatch,
    ) -> None:
        """Registra un recurs com a resoluble per picking."""
        if self._disposed:
            return

        # Si ja existeix amb la mateixa versió, idempotent
        existing = self._tables.get(resource_id)
        if existing and existing.version == version:
            return

        self._tables[resource_id] = StarPickTable(
            resource_id=resource_id,
            version=version,
            role=role,
            batch=batch,
        )
        log.debug(
            "MGP: [StarPickResolver] [register] "
            "[Taula registrada: %s v%s (%d estrelles)]",
            resource_id, version, len(batch),
        )

    def unregister(self, resource_id: str) -> None:
        """Desregistra un recurs (eviction, replacement)."""
        removed = self._tables.pop(resource_id, None)
        if removed:
            log.debug(
                "MGP: [StarPickResolver] [unregister] "
                "[Taula desregistrada: %s v%s]",
                removed.resource_id, removed.version,
            )

    def resolve(self, request: StarPickRequest) -> StarPickResponse:
        """Resol un pick estel·lar O(1) per índex.

        Valida:
        - resource existent
        - versió correcta
        - index >= 0
        - index < count
        - dades finites
        - source_id preservat
        """
        table = self._tables.get(request.resource_id)

        if table is None:
            return StarPickResponse(
                request_id=request.request_id,
                generation=request.generation,
                status="missing",
            )

        if table.version != request.resource_version:
            return StarPickResponse(
                request_id=request.request_id,
                generation=request.generation,
                status="stale",
            )

        idx = request.catalog_index
        batch = table.batch
        n = len(batch)

        if idx < 0 or idx >= n:
            log.warning(
                "MGP: [StarPickResolver] [resolve] "
                "[Index invàlid: %d (0..%d) recurs=%s]",
                idx, n - 1, request.resource_id,
            )
            return StarPickResponse(
                request_id=request.request_id,
                generation=request.generation,
                status="invalid",
            )

        # O(1) resolució per índex d'array
        ra = float(batch.ra[idx])
        dec = float(batch.dec[idx])
        mag = float(batch.mag[idx])
        bp_rp_val = float(batch.bp_rp[idx])
        source_id = int(batch.source_id[idx])

        # Validar dades finites
        if not (math.isfinite(ra) and math.isfinite(dec) and math.isfinite(mag)):
            log.warning(
                "MGP: [StarPickResolver] [resolve] "
                "[Dades no finites a index=%d recurs=%s]",
                idx, request.resource_id,
            )
            return StarPickResponse(
                request_id=request.request_id,
                generation=request.generation,
                status="invalid",
            )

        bp_rp = bp_rp_val if math.isfinite(bp_rp_val) else None

        resolved = ResolvedStarPick(
            resource_id=request.resource_id,
            version=request.resource_version,
            catalog_index=idx,
            source_id=source_id,
            ra_deg=ra,
            dec_deg=dec,
            magnitude=mag,
            bp_rp=bp_rp,
            source_role=table.role,
        )

        return StarPickResponse(
            request_id=request.request_id,
            generation=request.generation,
            status="ok",
            resolved=resolved,
        )

    def shutdown(self) -> None:
        """Allibera totes les taules."""
        if self._disposed:
            return
        self._disposed = True
        count = len(self._tables)
        self._tables.clear()
        log.debug(
            "MGP: [StarPickResolver] [shutdown] "
            "[%d taules alliberades]",
            count,
        )
