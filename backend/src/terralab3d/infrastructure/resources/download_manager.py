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
from terralab3d.infrastructure.resources.catalog import ResourceCatalog
from terralab3d.infrastructure.resources.installation_repository import ResourceInstallationRepository
from terralab3d.infrastructure.websocket_bridge import WebSocketBridge


log = logging.getLogger("terralab3d.resources.downloader")


class ResourceProcessingError(RuntimeError):
    """Error contextualitzat en generar l'asset derivat local."""


class ResourceVerificationError(RuntimeError):
    """Error contextualitzat en verificar mida o checksum local."""


class DownloadJobManager:
    """Propietari de les descàrregues asíncrones."""

    def __init__(
        self,
        catalog: ResourceCatalog,
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

    def start_download(self, resource_id: ResourceId, variant_id: VariantId) -> str:
        """Inicia o reprèn una descàrrega asíncrona."""
        job_id = f"{resource_id}_{variant_id}"
        
        if job_id in self._active_tasks and not self._active_tasks[job_id].done():
            log.info("MGP: [DownloadManager] [El job %s ja està actiu]", job_id)
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
        state = self._repository.get_resource_state(resource_id) or {}
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
        
        state = self._repository.get_resource_state(resource_id)
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
        if not variant or not variant.source_url:
            return
            
        filename = variant.source_url.split("/")[-1]
        temp_dir = resolve_download_temp_dir()
        final_dir = resolve_resource_install_dir(str(resource_id))
        
        temp_path = temp_dir / f"{filename}.part"
        final_path = final_dir / filename
        
        installed = self._repository.get_resource_state(resource_id) or {}
        candidates = [temp_path, final_path]
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
        log.info("MGP: [DownloadManager] [Iniciant job %s]", job_id)
        descriptor = self._catalog.get_descriptor(resource_id)
        if not descriptor:
            await self._fail_job(job_id, resource_id, variant_id, "NOT_FOUND", "Recurs no trobat al catàleg")
            return
            
        variant = next((v for v in descriptor.variants if v.id == variant_id), None)
        if not variant or not variant.source_url:
            await self._fail_job(job_id, resource_id, variant_id, "NO_URL", "La variant no té URL o no existeix")
            return
            
        # Determinar destí
        temp_dir = resolve_download_temp_dir()
        final_dir = resolve_resource_install_dir(str(resource_id))
        
        filename = variant.source_url.split("/")[-1]
        temp_path = temp_dir / f"{filename}.part"
        final_path = final_dir / filename

        # Si la font ja existeix (p. ex. un processament Planck fallit), no es
        # torna a transferir: es reprèn directament des de la frontera local.
        if final_path.exists():
            downloaded = final_path.stat().st_size
            try:
                content_sha256 = await self._hash_file(final_path, "sha256")
                await self._complete_installed_source(
                    job_id, resource_id, variant_id, final_path, filename,
                    downloaded, downloaded, content_sha256,
                )
            except ResourceProcessingError as exc:
                await self._fail_job(
                    job_id, resource_id, variant_id, "PROCESSING_ERROR", str(exc)
                )
            except Exception as exc:
                await self._fail_job(
                    job_id, resource_id, variant_id, "LOCAL_SOURCE_ERROR", str(exc)
                )
            return
        
        # Represa (Range)
        existing_bytes = 0
        if temp_path.exists():
            existing_bytes = temp_path.stat().st_size
            
        headers = {}
        if existing_bytes > 0:
            headers["Range"] = f"bytes={existing_bytes}-"
            
        self._repository.set_resource_state(
            resource_id, ResourceInstallState.DOWNLOADING, variant_id, downloaded_bytes=existing_bytes
        )

        try:
            timeout = aiohttp.ClientTimeout(
                total=None,
                connect=30.0,
                sock_connect=30.0,
                sock_read=120.0,
            )
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(variant.source_url, headers=headers) as response:
                    # Si el servidor no suporta Range i retorna 200, hem de reiniciar des de 0
                    if response.status == 200 and existing_bytes > 0:
                        log.warning("MGP: [DownloadManager] [Servidor no suporta Range per %s, reiniciant]", job_id)
                        existing_bytes = 0
                        temp_path.unlink(missing_ok=True)
                    elif response.status not in (200, 206):
                        await self._fail_job(
                            job_id, resource_id, variant_id, "HTTP_ERROR", f"Error HTTP {response.status}"
                        )
                        return

                    content_length = int(response.headers.get("Content-Length", 0))
                    total_bytes = existing_bytes + content_length if content_length > 0 else variant.expected_bytes
                    downloaded = existing_bytes
                    
                    # Obrir en mode append o write
                    mode = "ab" if existing_bytes > 0 else "wb"
                    with open(temp_path, mode) as f:
                        async for chunk in response.content.iter_chunked(1024 * 64):
                            if job_id in self._cancelled_jobs:
                                log.info("MGP: [DownloadManager] [Descàrrega %s cancel·lada]", job_id)
                                return # La tasca surt silenciosament per cancel·lació
                            
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            progress = (downloaded / total_bytes) if total_bytes else None
                            
                            await self._send_snapshot(DownloadJobSnapshot(
                                job_id=job_id, resource_id=resource_id, variant_id=variant_id,
                                state=ResourceInstallState.DOWNLOADING,
                                downloaded_bytes=downloaded, total_bytes=total_bytes, progress=progress,
                                current_file=filename, error_code=None, error_message=None
                            ))
                            
            # En aquest punt s'ha baixat tot
            # Verificació (Verifying)
            await self._send_snapshot(DownloadJobSnapshot(
                job_id=job_id, resource_id=resource_id, variant_id=variant_id,
                state=ResourceInstallState.VERIFYING,
                downloaded_bytes=downloaded, total_bytes=total_bytes, progress=1.0,
                current_file=filename, error_code=None, error_message=None
            ), force=True)
            self._repository.set_resource_state(
                resource_id, ResourceInstallState.VERIFYING, variant_id, downloaded_bytes=downloaded
            )

            content_sha256 = await self._hash_file(temp_path, "sha256")
            if variant.checksum:
                calculated = content_sha256 if variant.checksum.algorithm == "sha256" else await self._hash_file(
                    temp_path, variant.checksum.algorithm
                )
                if calculated != variant.checksum.value.lower():
                    raise ResourceVerificationError(
                        f"Checksum mismatch. Esperat: {variant.checksum.value}, Calculat: {calculated}"
                    )

            # Atomic Rename (utilitzem replace que és atòmic a nivell de POSIX i modern Windows)
            temp_path.replace(final_path)

            await self._complete_installed_source(
                job_id, resource_id, variant_id, final_path, filename,
                downloaded, total_bytes, content_sha256,
            )
            log.info("MGP: [DownloadManager] [Descàrrega %s completada i verificada]", job_id)
            
        except asyncio.CancelledError:
            log.info("MGP: [DownloadManager] [Descàrrega %s pausada/cancel·lada via task.cancel()]", job_id)
        except ResourceProcessingError as exc:
            log.error("MGP: [DownloadManager] [Error processant %s: %s]", job_id, exc)
            await self._fail_job(job_id, resource_id, variant_id, "PROCESSING_ERROR", str(exc))
        except ResourceVerificationError as exc:
            log.error("MGP: [DownloadManager] [Error verificant %s: %s]", job_id, exc)
            await self._fail_job(job_id, resource_id, variant_id, "VERIFY_ERROR", str(exc))
        except Exception as exc:
            log.error("MGP: [DownloadManager] [Error a la descàrrega %s: %s]", job_id, exc)
            await self._fail_job(job_id, resource_id, variant_id, "NETWORK_ERROR", str(exc))

    async def _complete_installed_source(
        self,
        job_id: str,
        resource_id: ResourceId,
        variant_id: VariantId,
        source_path: Path,
        filename: str,
        downloaded_bytes: int,
        total_bytes: int | None,
        content_sha256: str,
    ) -> None:
        processor = self._post_processors.get(resource_id)
        manifest_data: dict[str, object] = {
            "renderPath": str(source_path),
            "sourcePath": str(source_path),
            "sourceBytes": downloaded_bytes,
            "contentSha256": content_sha256,
        }
        if processor is not None:
            self._repository.set_resource_state(
                resource_id,
                ResourceInstallState.PROCESSING,
                variant_id,
                resolved_path=str(source_path),
                downloaded_bytes=downloaded_bytes,
            )
            await self._send_snapshot(DownloadJobSnapshot(
                job_id=job_id, resource_id=resource_id, variant_id=variant_id,
                state=ResourceInstallState.PROCESSING,
                downloaded_bytes=downloaded_bytes, total_bytes=total_bytes,
                progress=1.0, current_file=filename,
                error_code=None, error_message=None,
            ), force=True)
            try:
                processed = await asyncio.to_thread(
                    processor.process,
                    source_path,
                    resolve_derived_resource_dir(str(resource_id)),
                )
            except Exception as exc:
                raise ResourceProcessingError(
                    f"No s'ha pogut generar la cache de {resource_id}: {exc}"
                ) from exc
            if job_id in self._cancelled_jobs:
                return
            manifest_data.update(processed.metadata)
            manifest_data["renderPath"] = str(processed.render_path)

        self._repository.set_resource_state(
            resource_id,
            ResourceInstallState.READY,
            variant_id,
            resolved_path=str(source_path),
            downloaded_bytes=downloaded_bytes,
            verified_at=str(time.time()),
            manifest_data=manifest_data,
        )
        await self._send_snapshot(DownloadJobSnapshot(
            job_id=job_id, resource_id=resource_id, variant_id=variant_id,
            state=ResourceInstallState.READY,
            downloaded_bytes=downloaded_bytes, total_bytes=total_bytes,
            progress=1.0, current_file=filename,
            error_code=None, error_message=None,
        ), force=True)

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
        if variant is None or variant.source_url is None:
            return None
        partial = resolve_download_temp_dir() / f"{variant.source_url.rsplit('/', 1)[-1]}.part"
        return partial.stat().st_size if partial.is_file() else None

    async def _hash_file(self, path: Path, algorithm: str) -> str:
        loop = asyncio.get_running_loop()
        def _hash() -> str:
            h = hashlib.sha256() if algorithm == "sha256" else hashlib.md5()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            return h.hexdigest()
            
        return await loop.run_in_executor(None, _hash)

    async def _fail_job(
        self, job_id: str, resource_id: ResourceId, variant_id: VariantId, code: str, msg: str
    ) -> None:
        self._repository.set_resource_state(
            resource_id, ResourceInstallState.ERROR, variant_id, error_message=msg
        )
        await self._send_snapshot(DownloadJobSnapshot(
            job_id=job_id, resource_id=resource_id, variant_id=variant_id,
            state=ResourceInstallState.ERROR,
            downloaded_bytes=0, total_bytes=None, progress=None,
            current_file=None, error_code=code, error_message=msg
        ), force=True)
