"""Gestor de descàrregues de recursos.

Gestiona les peticions HTTP en streaming per a baixar recursos llargs sense bloquejar el fil principal,
permet represa (Range) i valida la integritat abans de marcar com a llest.
"""

import asyncio
import hashlib
import logging
import time
from pathlib import Path
from typing import Dict, Mapping, Set

import aiohttp

from terralab3d.domain.identifiers import ResourceId, VariantId
from terralab3d.application.ports.resource_processing import ResourcePostProcessor
from terralab3d.domain.resources.models import (
    DownloadJobSnapshot,
    ResourceInstallState,
)
from terralab3d.infrastructure.app_paths import (
    resolve_download_temp_dir,
    resolve_resource_install_dir,
    resolve_derived_resource_dir,
    resolve_data_root,
)
from terralab3d.infrastructure.resources.layer_database import LayerDatabase
from terralab3d.infrastructure.resources.installation_repository import ResourceInstallationRepository
from terralab3d.infrastructure.websocket_bridge import WebSocketBridge

from terralab3d.infrastructure.resources.acquirers import (
    StaticFileAcquirer,
    HttpBundleAcquirer,
    ParametricRasterAcquirer,
    ResourceAcquirer,
)

log = logging.getLogger("terralab3d.resources.downloader")


class DownloadJobManager:
    """Propietari de les descàrregues asíncrones."""

    def __init__(
        self,
        catalog: LayerDatabase,
        repository: ResourceInstallationRepository,
        bridge: WebSocketBridge,
        post_processors: Mapping[ResourceId, ResourcePostProcessor] | None = None,
    ) -> None:
        self._catalog = catalog
        self._repository = repository
        self._bridge = bridge
        self._post_processors = dict(post_processors or {})
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._cancelled_jobs: Set[str] = set()
        self._last_snapshot_time: Dict[str, float] = {}
        
        self._acquirers: Dict[str, ResourceAcquirer] = {
            "STATIC_FILE": StaticFileAcquirer(self, self._repository, self._bridge, self._post_processors),
            "HTTP_BUNDLE": HttpBundleAcquirer(self, self._repository, self._bridge, self._post_processors),
            "PARAMETRIC_DOWNLOAD": ParametricRasterAcquirer(self, self._repository, self._bridge, self._post_processors),
        }

    def start_download(self, resource_id: ResourceId, variant_id: VariantId) -> str:
        """Inicia o reprèn una descàrrega asíncrona."""
        job_id = f"{resource_id}_{variant_id}"
        
        if job_id in self._active_tasks and not self._active_tasks[job_id].done():
            log.debug("MGP: [DownloadManager] [El job %s ja està actiu]", job_id)
            return job_id

        self._cancelled_jobs.discard(job_id)
        task = asyncio.create_task(self._download_worker(job_id, resource_id, variant_id))
        self._active_tasks[job_id] = task
        return job_id

    def cancel_download(self, resource_id: ResourceId, variant_id: VariantId) -> None:
        job_id = f"{resource_id}_{variant_id}"
        self._cancelled_jobs.add(job_id)
        if job_id in self._active_tasks:
            self._active_tasks[job_id].cancel()
        state = self._repository.get_resource_state(resource_id, variant_id) or {}
        downloaded = self._partial_download_size(resource_id, variant_id)
        if downloaded is None:
            downloaded = int(state.get("downloadedBytes", 0) or 0)
        self._repository.set_resource_state(
            resource_id,
            ResourceInstallState.PARTIAL,
            variant_id,
            downloaded_bytes=downloaded,
        )
        asyncio.create_task(self._bridge.send_download_job_snapshot(DownloadJobSnapshot(
            job_id=job_id, resource_id=resource_id, variant_id=variant_id,
            state=ResourceInstallState.PARTIAL, downloaded_bytes=downloaded,
            total_bytes=None, progress=None, current_file=None,
            error_code=None, error_message=None,
        )))
            
    def pause_download(self, resource_id: ResourceId, variant_id: VariantId) -> None:
        # Per pausar, simplement cancel·lem la tasca asíncrona. 
        # Es reprendrà llegint els bytes descarregats.
        job_id = f"{resource_id}_{variant_id}"
        self._cancelled_jobs.add(job_id)
        if job_id in self._active_tasks:
            self._active_tasks[job_id].cancel()
        
        state = self._repository.get_resource_state(resource_id, variant_id)
        downloaded = self._partial_download_size(resource_id, variant_id)
        if downloaded is None:
            downloaded = state.get("downloadedBytes", 0) if state else 0
        
        self._repository.set_resource_state(
            resource_id, ResourceInstallState.PAUSED, variant_id, downloaded_bytes=downloaded
        )
        
        asyncio.create_task(self._bridge.send_download_job_snapshot(DownloadJobSnapshot(
            job_id=job_id, resource_id=resource_id, variant_id=variant_id,
            state=ResourceInstallState.PAUSED, downloaded_bytes=downloaded,
            total_bytes=None, progress=None, current_file=None,
            error_code=None, error_message=None
        )))

    def delete_resource(self, resource_id: ResourceId, variant_id: VariantId) -> None:
        """Elimina els fitxers descarregats (ja siguin parcials o complets) i reseteja l'estat."""
        job_id = f"{resource_id}_{variant_id}"
        self._cancelled_jobs.add(job_id)
        if job_id in self._active_tasks:
            self._active_tasks[job_id].cancel()
        
        descriptor = self._catalog.get_descriptor(resource_id)
        if not descriptor:
            return
            
        variant = next((v for v in descriptor.variants if v.id == variant_id), None)
        if not variant:
            return
            
        urls = []
        if variant.source_urls:
            urls.extend(variant.source_urls)
        elif variant.source_url:
            urls.append(variant.source_url)
            
        if not urls:
            return
            
        temp_dir = resolve_download_temp_dir()
        final_dir = resolve_resource_install_dir(str(resource_id))
        
        candidates = []
        for url in urls:
            filename = url.split("/")[-1]
            candidates.append(temp_dir / f"{filename}.part")
            candidates.append(final_dir / filename)
        
        installed = self._repository.get_resource_state(resource_id, variant_id) or {}
        for key in ("resolvedPath",):
            if installed.get(key):
                candidates.append(Path(str(installed[key])))
        manifest = installed.get("manifestData") or {}
        if isinstance(manifest, dict) and manifest.get("renderPath"):
            candidates.append(Path(str(manifest["renderPath"])))
        for candidate in candidates:
            self._unlink_managed_file(candidate)

        self._repository.clear_resource_state(resource_id, variant_id)
        
        asyncio.create_task(self._bridge.send_download_job_snapshot(DownloadJobSnapshot(
            job_id=job_id, resource_id=resource_id, variant_id=variant_id,
            state=ResourceInstallState.NOT_INSTALLED, downloaded_bytes=0,
            total_bytes=None, progress=0, current_file=None,
            error_code=None, error_message=None
        )))

    async def _send_snapshot(self, snapshot: DownloadJobSnapshot, force: bool = False) -> None:
        now = time.monotonic()
        last = self._last_snapshot_time.get(snapshot.job_id, 0.0)
        # Limitar a ~4 FPS (0.25 segons)
        if force or (now - last) >= 0.25:
            self._last_snapshot_time[snapshot.job_id] = now
            await self._bridge.send_download_job_snapshot(snapshot)

    async def _download_worker(self, job_id: str, resource_id: ResourceId, variant_id: VariantId) -> None:
        log.debug("MGP: [DownloadManager] [Iniciant job %s]", job_id)
        descriptor = self._catalog.get_descriptor(resource_id)
        if not descriptor:
            await self._fail_job(job_id, resource_id, variant_id, "NOT_FOUND", "Recurs no trobat al catàleg")
            return
            
        variant = next((v for v in descriptor.variants if v.id == variant_id), None)
        if not variant:
            await self._fail_job(job_id, resource_id, variant_id, "NOT_FOUND", "Variant no trobada")
            return
            
        acquirer = self._acquirers.get(descriptor.acquisition_kind.value)
        if not acquirer:
            await self._fail_job(job_id, resource_id, variant_id, "NO_ACQUIRER", f"No hi ha acquirer per {descriptor.acquisition_kind.value}")
            return
            
        await acquirer.acquire(job_id, descriptor, variant, self._active_tasks)

    @staticmethod
    def _unlink_managed_file(path: Path) -> None:
        root = resolve_data_root().resolve(strict=False)
        resolved = path.resolve(strict=False)
        if not resolved.is_relative_to(root):
            log.warning("MGP: [DownloadManager] [S'ignora una ruta fora de la llibreria: %s]", resolved)
            return
        if resolved.is_file():
            resolved.unlink()

    def _partial_download_size(
        self,
        resource_id: ResourceId,
        variant_id: VariantId,
    ) -> int | None:
        descriptor = self._catalog.get_descriptor(resource_id)
        if descriptor is None:
            return None
        variant = next((item for item in descriptor.variants if item.id == variant_id), None)
        if variant is None:
            return None
            
        urls = []
        if variant.source_urls:
            urls.extend(variant.source_urls)
        elif variant.source_url:
            urls.append(variant.source_url)
            
        if not urls:
            return None
            
        temp_dir = resolve_download_temp_dir()
        total_partial = 0
        has_any = False
        for url in urls:
            partial = temp_dir / f"{url.rsplit('/', 1)[-1]}.part"
            if partial.is_file():
                total_partial += partial.stat().st_size
                has_any = True
                
        return total_partial if has_any else None

    async def _fail_job(
        self, job_id: str, resource_id: ResourceId, variant_id: VariantId, code: str, msg: str
    ) -> None:
        log.error("MGP: [DownloadManager] [Job fallit %s] %s: %s", job_id, code, msg)
        self._repository.set_resource_state(
            resource_id, ResourceInstallState.ERROR, variant_id, error_message=msg
        )
        await self._send_snapshot(DownloadJobSnapshot(
            job_id=job_id, resource_id=resource_id, variant_id=variant_id,
            state=ResourceInstallState.ERROR,
            downloaded_bytes=0, total_bytes=None, progress=None,
            current_file=None, error_code=code, error_message=msg
        ), force=True)
