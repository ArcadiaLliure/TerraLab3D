"""Acquirers per a descarregar o generar recursos des de fonts externes."""

import asyncio
import hashlib
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Mapping

import aiohttp

from terralab3d.domain.identifiers import ResourceId, VariantId
from terralab3d.domain.resources.models import (
    ResourceInstallState,
    DownloadJobSnapshot,
    ResourceDescriptor,
    ResourceVariant,
)
from terralab3d.infrastructure.app_paths import (
    resolve_download_temp_dir,
    resolve_resource_install_dir,
    resolve_derived_resource_dir,
)

log = logging.getLogger("terralab3d.resources.acquirers")


class ResourceProcessingError(RuntimeError):
    """Error contextualitzat en generar l'asset derivat local."""


class ResourceVerificationError(RuntimeError):
    """Error contextualitzat en verificar mida o checksum local."""


class ResourceAcquirer(ABC):
    """Interfície comuna per a qualsevol estratègia d'adquisició."""

    def __init__(self, manager_callback, repository, bridge, post_processors):
        self.manager = manager_callback
        self.repository = repository
        self.bridge = bridge
        self.post_processors = post_processors

    @abstractmethod
    async def acquire(self, job_id: str, descriptor: ResourceDescriptor, variant: ResourceVariant, active_tasks: set) -> None:
        """Executa l'adquisició."""

    async def _send_snapshot(self, snapshot: DownloadJobSnapshot, force: bool = False) -> None:
        await self.manager._send_snapshot(snapshot, force)

    async def _fail_job(self, job_id: str, resource_id: ResourceId, variant_id: VariantId, code: str, msg: str) -> None:
        await self.manager._fail_job(job_id, resource_id, variant_id, code, msg)
        
    async def _hash_file(self, path: Path, algorithm: str) -> str:
        loop = asyncio.get_running_loop()
        def _hash() -> str:
            h = hashlib.sha256() if algorithm == "sha256" else hashlib.md5()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            return h.hexdigest()
            
        return await loop.run_in_executor(None, _hash)

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
        active_tasks: set,
    ) -> None:
        processor = self.post_processors.get(resource_id)
        manifest_data: dict[str, object] = {
            "renderPath": str(source_path),
            "sourcePath": str(source_path),
            "sourceBytes": downloaded_bytes,
            "contentSha256": content_sha256,
        }
        if processor is not None:
            self.repository.set_resource_state(
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
            if job_id not in active_tasks:
                return
            manifest_data.update(processed.metadata)
            manifest_data["renderPath"] = str(processed.render_path)

        self.repository.set_resource_state(
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


class HttpBundleAcquirer(ResourceAcquirer):
    """Descarrega paquets directament via HTTP (també per StaticFileAcquirer per ara)."""

    async def acquire(self, job_id: str, descriptor: ResourceDescriptor, variant: ResourceVariant, active_tasks: set) -> None:
        resource_id = descriptor.id
        variant_id = variant.id
        
        urls_to_download = []
        if variant.source_urls:
            urls_to_download.extend(variant.source_urls)
        elif variant.source_url:
            urls_to_download.append(variant.source_url)
            
        if not urls_to_download:
            await self._fail_job(job_id, resource_id, variant_id, "NO_URL", "La variant no té URL")
            return
            
        temp_dir = resolve_download_temp_dir()
        final_dir = resolve_resource_install_dir(str(resource_id))
        
        total_downloaded = 0
        overall_total_bytes = variant.expected_bytes

        for url in urls_to_download:
            filename = url.split("/")[-1]
            temp_path = temp_dir / f"{filename}.part"
            final_path = final_dir / filename
            if final_path.exists():
                total_downloaded += final_path.stat().st_size
            elif temp_path.exists():
                total_downloaded += temp_path.stat().st_size

        self.repository.set_resource_state(
            resource_id, ResourceInstallState.DOWNLOADING, variant_id, downloaded_bytes=total_downloaded
        )
        
        try:
            timeout = aiohttp.ClientTimeout(total=None, connect=30.0, sock_connect=30.0, sock_read=120.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for url in urls_to_download:
                    filename = url.split("/")[-1]
                    temp_path = temp_dir / f"{filename}.part"
                    final_path = final_dir / filename
                    
                    if final_path.exists():
                        continue
                        
                    existing_bytes = 0
                    if temp_path.exists():
                        existing_bytes = temp_path.stat().st_size
                        
                    headers = {}
                    if existing_bytes > 0:
                        headers["Range"] = f"bytes={existing_bytes}-"
                        
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200 and existing_bytes > 0:
                            log.warning("MGP: [DownloadManager] [Servidor no suporta Range per %s, reiniciant]", job_id)
                            total_downloaded -= existing_bytes
                            existing_bytes = 0
                            temp_path.unlink(missing_ok=True)
                        elif response.status not in (200, 206):
                            msg = f"Error HTTP {response.status} en baixar {filename}: {response.reason}"
                            log.error("MGP: [DownloadManager] [Error a la descàrrega %s: %s]", job_id, msg)
                            await self._fail_job(job_id, resource_id, variant_id, "HTTP_ERROR", msg)
                            return
                            
                        mode = "ab" if existing_bytes > 0 else "wb"
                        with open(temp_path, mode) as f:
                            async for chunk in response.content.iter_chunked(1024 * 64):
                                if job_id not in active_tasks:
                                    log.debug("MGP: [DownloadManager] [Descàrrega %s cancel·lada]", job_id)
                                    return
                                
                                f.write(chunk)
                                total_downloaded += len(chunk)
                                
                                progress = (total_downloaded / overall_total_bytes) if overall_total_bytes else None
                                
                                await self._send_snapshot(DownloadJobSnapshot(
                                    job_id=job_id, resource_id=resource_id, variant_id=variant_id,
                                    state=ResourceInstallState.DOWNLOADING,
                                    downloaded_bytes=total_downloaded, total_bytes=overall_total_bytes, progress=progress,
                                    current_file=filename, error_code=None, error_message=None
                                ))
                                
                    temp_path.replace(final_path)

            await self._send_snapshot(DownloadJobSnapshot(
                job_id=job_id, resource_id=resource_id, variant_id=variant_id,
                state=ResourceInstallState.VERIFYING,
                downloaded_bytes=total_downloaded, total_bytes=overall_total_bytes, progress=1.0,
                current_file="Tot completat", error_code=None, error_message=None
            ), force=True)
            
            self.repository.set_resource_state(
                resource_id, ResourceInstallState.VERIFYING, variant_id, downloaded_bytes=total_downloaded
            )

            source_path = final_path if len(urls_to_download) == 1 else final_dir
            content_sha256 = None
            
            if len(urls_to_download) == 1:
                content_sha256 = await self._hash_file(final_path, "sha256")
                if variant.checksum:
                    calculated = content_sha256 if variant.checksum.algorithm == "sha256" else await self._hash_file(
                        final_path, variant.checksum.algorithm
                    )
                    if calculated != variant.checksum.value.lower():
                        raise ResourceVerificationError(
                            f"Checksum mismatch. Esperat: {variant.checksum.value}, Calculat: {calculated}"
                        )

            display_name = "Pack de múltiples URLs" if len(urls_to_download) > 1 else urls_to_download[0].split("/")[-1]
            await self._complete_installed_source(
                job_id, resource_id, variant_id, source_path, display_name,
                total_downloaded, overall_total_bytes, content_sha256, active_tasks
            )
            log.debug("MGP: [DownloadManager] [Descàrrega %s completada i verificada]", job_id)
            
        except asyncio.CancelledError:
            log.debug("MGP: [DownloadManager] [Descàrrega %s pausada/cancel·lada via task.cancel()]", job_id)
        except ResourceProcessingError as exc:
            log.error("MGP: [DownloadManager] [Error processant %s: %s]", job_id, exc)
            await self._fail_job(job_id, resource_id, variant_id, "PROCESSING_ERROR", str(exc))
        except ResourceVerificationError as exc:
            log.error("MGP: [DownloadManager] [Error verificant %s: %s]", job_id, exc)
            await self._fail_job(job_id, resource_id, variant_id, "VERIFY_ERROR", str(exc))
        except Exception as exc:
            log.error("MGP: [DownloadManager] [Error a la descàrrega %s: %s]", job_id, exc)
            await self._fail_job(job_id, resource_id, variant_id, "NETWORK_ERROR", str(exc))


class StaticFileAcquirer(HttpBundleAcquirer):
    """Comportament idèntic per ara."""
    pass


class ParametricRasterAcquirer(ResourceAcquirer):
    """Esquelet per a les descàrregues paramètriques (e.g. Copernicus Data Space per bounding box)."""
    
    async def acquire(self, job_id: str, descriptor: ResourceDescriptor, variant: ResourceVariant, active_tasks: set) -> None:
        resource_id = descriptor.id
        variant_id = variant.id
        log.warning("MGP: [ParametricRasterAcquirer] Funcionalitat encara no implementada completament per %s", resource_id)
        await self._fail_job(
            job_id, resource_id, variant_id, "NOT_IMPLEMENTED", "Parametric downloads not yet supported"
        )
