"""Coordinador d'estrelles per a TerraLab3D.

Orquestra:
- Càrrega del catàleg general Gaia o fallback
- Construcció de buffers binaris GPU-ready
- Publicació de recursos via bridge
- Transformació equatorial→ENU
- Càrrega progressiva sense fer desaparèixer el general
- Cancel·lació de queries obsoletes

Regla central:
  les estrelles són recursos celestes persistents;
  el temps modifica una transformació;
  la càmera visual modifica la vista;
  la translació local no modifica la ciència;
  el catàleg no torna a viatjar.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Callable, Awaitable

import numpy as np

from terralab3d.domain.stars.models import (
    CelestialFrameTransform,
    StarBatch,
    StarCatalogStatus,
    StarResourceDescriptor,
    StarResourceRole,
)
from terralab3d.domain.stars.calculations import (
    bp_rp_to_rgb_uint8,
    compute_celestial_transform_matrix,
    ra_dec_to_unit_vectors,
)
from terralab3d.infrastructure.adapters.star_catalog_adapter import (
    FallbackStarCatalogAdapter,
    GaiaStarCatalogAdapter,
    create_star_catalog_adapter,
)

# Import condicional per evitar circular — el resolver s'injecta via set_pick_resolver
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from terralab3d.application.star_pick_resolver import StarPickResolver

log = logging.getLogger("terralab3d.stars")

# Tipus de callback per publicar recursos
ResourcePublisher = Callable[
    [str, str, dict[str, Any], bytes],
    Awaitable[None],
]
StatusPublisher = Callable[[dict[str, Any]], Awaitable[None]]
TransformPublisher = Callable[[dict[str, Any]], Awaitable[None]]


class StarCoordinator:
    """Coordinador de dades estel·lars per a TerraLab3D.

    Gestiona:
    - Descobriment i càrrega de Gaia/fallback
    - Conversió a buffers GPU binaris (una vegada per versió)
    - Publicació incremental sense fer desaparèixer recursos
    - Transformació equatorial→ENU
    """

    def __init__(
        self,
        gaia_path: str | None = None,
    ) -> None:
        self._adapter = create_star_catalog_adapter(gaia_path)
        self._resource_publisher: ResourcePublisher | None = None
        self._status_publisher: StatusPublisher | None = None
        self._transform_publisher: TransformPublisher | None = None

        # Recursos registrats
        self._resources: dict[str, StarResourceDescriptor] = {}
        self._resource_version: int = 0

        # Batches retinguts per al picking O(1) (Pas 6)
        self._batches: dict[str, StarBatch] = {}
        self._pick_resolver: StarPickResolver | None = None

        # Estat
        self._general_star_count = 0
        self._fallback_star_count = 0
        self._deep_resident_count = 0
        self._effective_source = "none"
        self._transform_generation = 0
        self._last_lat_deg: float | None = None
        self._last_lst_deg: float | None = None

        self._started = False
        self._disposed = False

    def set_publishers(
        self,
        resource_publisher: ResourcePublisher,
        status_publisher: StatusPublisher,
        transform_publisher: TransformPublisher,
    ) -> None:
        """Configura els publishers per publicar recursos, estat i transforms."""
        self._resource_publisher = resource_publisher
        self._status_publisher = status_publisher
        self._transform_publisher = transform_publisher

    def set_pick_resolver(self, resolver: StarPickResolver) -> None:
        """Connecta el resolutor de picks (Pas 6)."""
        self._pick_resolver = resolver

    async def start(self) -> None:
        """Inicia la càrrega del catàleg. Seqüència:
        1. fallback visible si Gaia no disponible
        2. Gaia general loading → ready
        """
        if self._started or self._disposed:
            return
        self._started = True

        availability = self._adapter.get_availability()
        log.debug(
            "MGP: [StarCoordinator] [start] "
            "[Gaia=%s, adapter=%s]",
            availability.value,
            type(self._adapter).__name__,
        )

        if isinstance(self._adapter, FallbackStarCatalogAdapter):
            # Mode fallback
            await self._load_fallback()
        elif isinstance(self._adapter, GaiaStarCatalogAdapter):
            # Mode Gaia — carregar general
            await self._load_gaia_general()
        else:
            await self._load_fallback()

        await self._publish_status()

    async def publish_current_state(self) -> None:
        """República l'estat actual i els recursos al frontend.
        Útil quan el client es desconnecta i es torna a connectar (F5).
        """
        if not self._started or self._disposed:
            return
            
        # Re-enviar recursos carregats (re-construint el buffer des del batch en RAM)
        for res_id, batch in list(self._batches.items()):
            descriptor = self._resources.get(res_id)
            if descriptor:
                await self._build_and_publish_resource(
                    resource_id=res_id,
                    role=descriptor.role,
                    batch=batch,
                )
                
        # Re-enviar l'estat actual
        await self._publish_status()

    async def update_celestial_transform(
        self,
        latitude_deg: float,
        lst_deg: float,
        *,
        force_publish: bool = False,
        transition_ms: float = 1000.0,
    ) -> bool:
        """Actualitza la transformació equatorial→ENU.

        Es crida quan canvia LST o latitud. NO per frame visual.
        NO toca buffers estel·lars.

        ``force_publish`` torna a enviar el darrer marc a un frontend nou sense
        crear una generació científica falsa. Això evita que una reconnexió
        mostri cap capa celeste amb la matriu identitat.
        """
        if self._disposed:
            return False

        changed = not (
            self._last_lat_deg is not None
            and self._last_lst_deg is not None
            and abs(latitude_deg - self._last_lat_deg) < 1e-6
            and abs(lst_deg - self._last_lst_deg) < 1e-4
        )
        if not changed and not force_publish:
            return False

        if changed:
            self._last_lat_deg = latitude_deg
            self._last_lst_deg = lst_deg
            self._transform_generation += 1

        matrix = compute_celestial_transform_matrix(latitude_deg, lst_deg)
        transform = CelestialFrameTransform(
            generation=self._transform_generation,
            matrix_3x3=matrix,
        )

        if self._transform_publisher:
            await self._transform_publisher({
                "type": "celestial_frame_transform",
                "generation": transform.generation,
                "matrix3x3": list(transform.matrix_3x3),
                "transitionMs": max(0.0, float(transition_ms)),
            })
        return True

    def get_status(self) -> StarCatalogStatus:
        """Retorna l'estat actual del catàleg."""
        return StarCatalogStatus(
            gaia_availability=self._adapter.get_availability(),
            effective_source=self._effective_source,
            general_star_count=self._general_star_count,
            fallback_star_count=self._fallback_star_count,
            deep_resident_count=self._deep_resident_count,
        )

    async def shutdown(self) -> None:
        """Tanca l'adaptador i allibera recursos."""
        if self._disposed:
            return
        self._disposed = True
        self._adapter.close()
        self._resources.clear()
        self._batches.clear()
        if self._pick_resolver:
            self._pick_resolver.shutdown()
        log.debug("MGP: [StarCoordinator] [shutdown] [Coordinador tancat]")

    # ─── Private ──────────────────────────────────────────────────────

    async def _load_fallback(self) -> None:
        """Carrega i publica el catàleg fallback."""
        t0 = time.perf_counter()
        batch = self._adapter.load_fallback_catalog()
        if batch is None:
            log.warning(
                "MGP: [StarCoordinator] [_load_fallback] "
                "[Cap catàleg fallback disponible]"
            )
            return

        self._fallback_star_count = len(batch)
        self._effective_source = "fallback"

        await self._build_and_publish_resource(
            resource_id="stars:fallback",
            role=StarResourceRole.FALLBACK,
            batch=batch,
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000
        log.debug(
            "MGP: [StarCoordinator] [_load_fallback] "
            "[Fallback publicat: %d estrelles, %.1f ms]",
            len(batch), elapsed_ms,
        )

    async def _load_gaia_general(self) -> None:
        """Carrega i publica el catàleg general Gaia."""
        t0 = time.perf_counter()

        # Primer, carregar fallback per tenir cel visible immediatament
        fallback_adapter = FallbackStarCatalogAdapter()
        fallback_batch = fallback_adapter.load_fallback_catalog()
        if fallback_batch is not None:
            self._fallback_star_count = len(fallback_batch)
            await self._build_and_publish_resource(
                resource_id="stars:fallback",
                role=StarResourceRole.FALLBACK,
                batch=fallback_batch,
            )
            self._effective_source = "fallback"
            await self._publish_status()

        # Ara carregar Gaia general
        batch = self._adapter.load_general_catalog(mag_limit=8.0)
        if batch is None:
            log.warning(
                "MGP: [StarCoordinator] [_load_gaia_general] "
                "[No s'ha pogut carregar general Gaia — mantenint fallback]"
            )
            return

        self._general_star_count = len(batch)
        self._effective_source = "gaia"

        await self._build_and_publish_resource(
            resource_id="stars:general",
            role=StarResourceRole.GENERAL,
            batch=batch,
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000
        log.debug(
            "MGP: [StarCoordinator] [_load_gaia_general] "
            "[General publicat: %d estrelles, %.1f ms]",
            len(batch), elapsed_ms,
        )

    async def _build_and_publish_resource(
        self,
        resource_id: str,
        role: StarResourceRole,
        batch: StarBatch,
    ) -> None:
        """Construeix buffers GPU i publica via bridge.

        Conversions (UNA VEGADA per versió de recurs):
        - RA/Dec → vectors unitaris equatorials xyz float32[N,3]
        - BP-RP → RGB uint8[N,3]
        - mag → float32[N]
        - catalogIndex → uint32[N]
        """
        n = len(batch)
        if n == 0:
            return

        # 1. Posicions: vectors unitaris equatorials
        positions = ra_dec_to_unit_vectors(batch.ra, batch.dec)  # [N,3] float32

        # 2. Magnituds
        magnitudes = np.asarray(batch.mag, dtype=np.float32)  # [N] float32

        # 3. Colors: BP-RP → RGB uint8
        colors = bp_rp_to_rgb_uint8(batch.bp_rp)  # [N,3] uint8

        # 4. Catalog indices (GPU-side ID, uint32)
        catalog_indices = np.arange(n, dtype=np.uint32)  # [N] uint32

        # Construir buffer binari concatenat:
        # [positions_f32 | magnitudes_f32 | colors_u8 | padding | indices_u32]
        pos_bytes = positions.tobytes()       # N*12 bytes
        mag_bytes = magnitudes.tobytes()      # N*4 bytes
        col_bytes = colors.tobytes()          # N*3 bytes
        
        # PADDING per colors (ha de ser múltiple de 4 bytes)
        padding_len = (4 - (len(col_bytes) % 4)) % 4
        padding_bytes = b'\x00' * padding_len

        idx_bytes = catalog_indices.tobytes() # N*4 bytes

        total_bytes = len(pos_bytes) + len(mag_bytes) + len(col_bytes) + padding_len + len(idx_bytes)
        buffer = pos_bytes + mag_bytes + col_bytes + padding_bytes + idx_bytes

        # Hash del contingut
        content_hash = hashlib.sha256(buffer).hexdigest()[:16]

        # Versionar
        self._resource_version += 1
        version = str(self._resource_version)

        descriptor = StarResourceDescriptor(
            resource_id=resource_id,
            version=version,
            owner="star_coordinator",
            star_count=n,
            byte_length=total_bytes,
            role=role,
            content_hash=content_hash,
        )
        self._resources[resource_id] = descriptor

        # Retenir batch per al picking (Pas 6)
        self._batches[resource_id] = batch
        if self._pick_resolver:
            self._pick_resolver.register(
                resource_id=resource_id,
                version=version,
                role=role.value,
                batch=batch,
            )

        # Publicar
        if self._resource_publisher:
            idx_offset = len(pos_bytes) + len(mag_bytes) + len(col_bytes) + padding_len
            metadata = {
                "type": "star_resource",
                "resourceId": resource_id,
                "version": version,
                "role": role.value,
                "starCount": n,
                "byteLength": total_bytes,
                "contentHash": content_hash,
                "bufferLayout": {
                    "positions": {"offset": 0, "length": len(pos_bytes), "dtype": "float32", "components": 3},
                    "magnitudes": {"offset": len(pos_bytes), "length": len(mag_bytes), "dtype": "float32", "components": 1},
                    "colors": {"offset": len(pos_bytes) + len(mag_bytes), "length": len(col_bytes), "dtype": "uint8", "components": 3},
                    "catalogIndices": {"offset": idx_offset, "length": len(idx_bytes), "dtype": "uint32", "components": 1},
                },
            }
            await self._resource_publisher(resource_id, version, metadata, buffer)

        log.debug(
            "MGP: [StarCoordinator] [_build_and_publish_resource] "
            "[%s: %d estrelles, %d bytes, hash=%s]",
            resource_id, n, total_bytes, content_hash,
        )

    async def _publish_status(self) -> None:
        """Publica l'estat actual del catàleg a la UI."""
        if self._status_publisher:
            status = self.get_status()
            await self._status_publisher({
                "type": "star_catalog_status",
                "gaiaAvailability": status.gaia_availability.value,
                "effectiveSource": status.effective_source,
                "generalStarCount": status.general_star_count,
                "fallbackStarCount": status.fallback_star_count,
                "deepResidentCount": status.deep_resident_count,
            })
