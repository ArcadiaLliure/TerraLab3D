"""Acquirers per a descarregar o generar recursos des de fonts externes."""

import asyncio
import hashlib
import logging
import shutil
import tempfile
import time
import zipfile
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Collection
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

import aiohttp

from terralab3d.domain.refinement.downloads import ParametricDownloadPlan
from terralab3d.domain.refinement.errors import RefinementValidationError
from terralab3d.application.refinement.auth_coordinator import AuthenticationRequiredError
from terralab3d.domain.identifiers import ResourceId, VariantId
from terralab3d.domain.resources.models import (
    DownloadAssetProgress,
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


class ResourceConfigurationError(RuntimeError):
    """The frozen plan cannot run until external configuration is supplied."""


class ResourcePlanError(RuntimeError):
    """The persisted parametric plan no longer matches its resource variant."""


def safe_extract_zip(archive: Path, destination: Path) -> tuple[Path, ...]:
    """Extract an archive atomically after rejecting traversal and symlinks."""

    destination_parent = destination.parent.resolve(strict=False)
    destination_parent.mkdir(parents=True, exist_ok=True)
    if destination.resolve(strict=False).parent != destination_parent:
        raise ResourceVerificationError("ZIP destination is outside its staging parent")
    if destination.is_dir():
        return tuple(path for path in destination.rglob("*") if path.is_file())
    if destination.is_file():
        destination.unlink(missing_ok=True)

    staging = Path(tempfile.mkdtemp(prefix=".extract-", dir=destination_parent))
    extracted: list[Path] = []
    try:
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                member_path = Path(member.filename)
                unix_mode = member.external_attr >> 16
                is_symlink = (unix_mode & 0o170000) == 0o120000
                if (
                    member_path.is_absolute()
                    or member_path.drive
                    or ".." in member_path.parts
                    or is_symlink
                ):
                    raise ResourceVerificationError(
                        f"Unsafe ZIP member rejected: {member.filename}"
                    )
                target = (staging / member_path).resolve(strict=False)
                if not target.is_relative_to(staging.resolve(strict=False)):
                    raise ResourceVerificationError(
                        f"Unsafe ZIP member rejected: {member.filename}"
                    )
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(member) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                extracted.append(target)
        staging.replace(destination)
        return tuple(destination / path.relative_to(staging) for path in extracted)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def resource_variant_downloads(
    variant: ResourceVariant,
) -> tuple[tuple[str, str], ...]:
    """Resolve stable URL/file pairs, including names frozen in parametric plans."""

    serialized = dict(variant.metadata).get("parametricPlan")
    if isinstance(serialized, str):
        try:
            plan = ParametricDownloadPlan.from_json(serialized)
        except (RefinementValidationError, TypeError, ValueError):
            plan = None
        if plan is not None:
            return tuple((asset.download_url, asset.file_name) for asset in plan.assets)
    urls = variant.source_urls or ((variant.source_url,) if variant.source_url else ())
    names: set[str] = set()
    downloads: list[tuple[str, str]] = []
    for index, url in enumerate(urls):
        file_name = Path(urlsplit(url).path).name or f"asset-{index}.bin"
        if file_name in names:
            file_name = f"{index}-{file_name}"
        names.add(file_name)
        downloads.append((url, file_name))
    return tuple(downloads)


class ResourceAcquirer(ABC):
    """Interfície comuna per a qualsevol estratègia d'adquisició."""

    def __init__(self, manager_callback, repository, bridge, post_processors):
        self.manager = manager_callback
        self.repository = repository
        self.bridge = bridge
        self.post_processors = post_processors

    @abstractmethod
    async def acquire(self, job_id: str, descriptor: ResourceDescriptor, variant: ResourceVariant, active_tasks: Collection[str]) -> None:
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
        content_sha256: str | None,
        active_tasks: Collection[str],
        manifest_metadata: Mapping[str, object] | None = None,
    ) -> None:
        processor = self.post_processors.get(resource_id)
        manifest_data: dict[str, object] = {
            "renderPath": str(source_path),
            "sourcePath": str(source_path),
            "sourceBytes": downloaded_bytes,
            "contentSha256": content_sha256,
        }
        if manifest_metadata:
            manifest_data.update(manifest_metadata)

        if processor:
            self.repository.set_resource_state(
                resource_id,
                ResourceInstallState.PROCESSING,
                variant_id,
                resolved_path=str(source_path),
                downloaded_bytes=downloaded_bytes,
            )
            loop = asyncio.get_running_loop()

            async def _send_processing_progress(current_file: str, progress_ratio: float | None = None) -> None:
                await self._send_snapshot(
                    DownloadJobSnapshot(
                        job_id=job_id,
                        resource_id=resource_id,
                        variant_id=variant_id,
                        state=ResourceInstallState.PROCESSING,
                        downloaded_bytes=downloaded_bytes,
                        total_bytes=total_bytes,
                        progress=progress_ratio if progress_ratio is not None else 1.0,
                        current_file=current_file,
                        error_code=None,
                        error_message=None,
                    ),
                    force=True,
                )

            def _on_mosaic_progress(current: int, total: int, phase: str) -> None:
                ratio = current / total if total > 0 else 0.0
                msg = f"{phase} ({current}/{total} - {ratio * 100:.0f}%)" if total > 0 else phase
                asyncio.run_coroutine_threadsafe(_send_processing_progress(msg, ratio), loop)

            await _send_processing_progress("Iniciant harmonització del mosaic...", 0.0)
            try:
                processed = await asyncio.to_thread(
                    processor.process,
                    source_path,
                    resolve_derived_resource_dir(str(resource_id)),
                    _on_mosaic_progress,
                )
            except TypeError:
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

    async def acquire(self, job_id: str, descriptor: ResourceDescriptor, variant: ResourceVariant, active_tasks: Collection[str]) -> None:
        resource_id = descriptor.id
        variant_id = variant.id
        
        downloads = resource_variant_downloads(variant)
        urls_to_download = [url for url, _file_name in downloads]
            
        if not urls_to_download:
            await self._fail_job(job_id, resource_id, variant_id, "NO_URL", "La variant no té URL")
            return
            
        temp_dir = resolve_download_temp_dir()
        final_dir = resolve_resource_install_dir(str(resource_id))
        final_path = final_dir
        
        total_downloaded = 0
        overall_total_bytes = variant.expected_bytes

        for _url, filename in downloads:
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
                for url, filename in downloads:
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

            display_name = (
                "Pack de múltiples URLs"
                if len(urls_to_download) > 1
                else downloads[0][1]
            )
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
    """Execute an immutable, user-reviewed plan with the shared job manager."""

    _MAX_PARALLEL_ASSET_DOWNLOADS = 4

    def __init__(self, manager_callback, repository, bridge, post_processors, auth_coordinator=None):
        super().__init__(manager_callback, repository, bridge, post_processors)
        self._auth_coordinator = auth_coordinator

    @staticmethod
    def _plan_from_variant(variant: ResourceVariant) -> ParametricDownloadPlan:
        serialized = dict(variant.metadata).get("parametricPlan")
        if not isinstance(serialized, str):
            raise ResourcePlanError("The resource variant has no frozen parametric plan")
        try:
            plan = ParametricDownloadPlan.from_json(serialized)
        except (RefinementValidationError, TypeError, ValueError) as exc:
            raise ResourcePlanError(f"Invalid frozen parametric plan: {exc}") from exc
        if tuple(asset.download_url for asset in plan.assets) != variant.source_urls:
            raise ResourcePlanError("Frozen assets no longer match the resource variant URLs")
        if len({asset.file_name for asset in plan.assets}) != len(plan.assets):
            raise ResourcePlanError("Frozen assets must have unique file names")
        invalid_algos = [a.checksum_algorithm for a in plan.assets if a.checksum_algorithm and str(a.checksum_algorithm).strip().lower() not in {"md5", "sha256", "etag"}]
        if invalid_algos:
            raise ResourcePlanError(f"The plan contains an unsupported checksum algorithm: {invalid_algos}")
        return plan

    async def acquire(
        self,
        job_id: str,
        descriptor: ResourceDescriptor,
        variant: ResourceVariant,
        active_tasks: Collection[str],
    ) -> None:
        resource_id = descriptor.id
        variant_id = variant.id
        try:
            plan = self._plan_from_variant(variant)
            if (
                plan.requires_large_download_confirmation
                and plan.processing_options.get("largeDownloadConfirmed") is not True
            ):
                raise ResourceConfigurationError(
                    "This large download requires explicit confirmation"
                )
            requires_authentication = any(
                asset.requires_authentication for asset in plan.assets
            )
            if requires_authentication and not self._auth_coordinator:
                raise ResourceConfigurationError(
                    "Authentication required but no coordinator provided"
                )

            temp_dir = resolve_download_temp_dir()
            final_dir = resolve_resource_install_dir(str(resource_id))
            final_paths = tuple(final_dir / asset.file_name for asset in plan.assets)
            total_downloaded = sum(
                self._existing_bytes(temp_dir, asset.file_name, final_path)
                for asset, final_path in zip(plan.assets, final_paths, strict=True)
            )

            token = ""
            if requires_authentication:
                self.repository.set_resource_state(
                    resource_id,
                    ResourceInstallState.AUTHENTICATING,
                    variant_id,
                    downloaded_bytes=total_downloaded,
                )
                await self._send_snapshot(
                    DownloadJobSnapshot(
                        job_id=job_id,
                        resource_id=resource_id,
                        variant_id=variant_id,
                        state=ResourceInstallState.AUTHENTICATING,
                        downloaded_bytes=total_downloaded,
                        total_bytes=plan.estimated_bytes,
                        progress=(
                            total_downloaded / plan.estimated_bytes
                            if plan.estimated_bytes
                            else None
                        ),
                        current_file="Copernicus Data Space Ecosystem",
                        error_code=None,
                        error_message=None,
                    ),
                    force=True,
                )
                token = await self._auth_coordinator.get_valid_token(interactive=True)

            self.repository.set_resource_state(
                resource_id,
                ResourceInstallState.DOWNLOADING,
                variant_id,
                downloaded_bytes=total_downloaded,
            )
            await self._send_snapshot(
                DownloadJobSnapshot(
                    job_id=job_id,
                    resource_id=resource_id,
                    variant_id=variant_id,
                    state=ResourceInstallState.DOWNLOADING,
                    downloaded_bytes=total_downloaded,
                    total_bytes=plan.estimated_bytes,
                    progress=(
                        total_downloaded / plan.estimated_bytes
                        if plan.estimated_bytes
                        else None
                    ),
                    current_file=plan.assets[0].file_name,
                    error_code=None,
                    error_message=None,
                ),
                force=True,
            )

            timeout = aiohttp.ClientTimeout(
                total=None,
                connect=30.0,
                sock_connect=30.0,
                sock_read=120.0,
            )
            async with aiohttp.ClientSession(timeout=timeout) as session:
                total_downloaded = await self._download_assets_in_parallel(
                    session=session,
                    job_id=job_id,
                    resource_id=resource_id,
                    variant_id=variant_id,
                    plan=plan,
                    final_paths=final_paths,
                    token=token,
                    temp_dir=temp_dir,
                    active_tasks=active_tasks,
                )

            if job_id not in active_tasks:
                return
            self.repository.set_resource_state(
                resource_id,
                ResourceInstallState.VERIFYING,
                variant_id,
                downloaded_bytes=total_downloaded,
            )
            await self._send_snapshot(
                DownloadJobSnapshot(
                    job_id=job_id,
                    resource_id=resource_id,
                    variant_id=variant_id,
                    state=ResourceInstallState.VERIFYING,
                    downloaded_bytes=total_downloaded,
                    total_bytes=plan.estimated_bytes,
                    progress=1.0,
                    current_file="Tot completat",
                    error_code=None,
                    error_message=None,
                ),
                force=True,
            )

            hashes = await self._verify_assets(plan, final_paths)
            source_paths: tuple[Path, ...] = final_paths
            if plan.processing_options.get("extractArchives") is True:
                source_paths = await self._extract_downloaded_archives(final_paths)
            source_path = source_paths[0] if len(source_paths) == 1 else final_dir
            manifest_metadata: dict[str, object] = {
                "parametricPlan": plan.to_dict(),
                "downloadedFiles": [
                    {
                        "assetId": asset.asset_id,
                        "fileName": asset.file_name,
                        "bytes": final_path.stat().st_size,
                        "sha256": hashes[asset.file_name],
                        "license": asset.license_id,
                        "licenseUrl": asset.license_url,
                        "provenanceUrl": asset.provenance_url,
                    }
                    for asset, final_path in zip(plan.assets, final_paths, strict=True)
                ],
            }
            await self._complete_installed_source(
                job_id,
                resource_id,
                variant_id,
                source_path,
                "Pla paramètric completat",
                total_downloaded,
                plan.estimated_bytes,
                hashes[plan.assets[0].file_name] if len(plan.assets) == 1 else None,
                active_tasks,
                manifest_metadata,
            )
        except asyncio.CancelledError:
            log.debug("MGP: [ParametricRasterAcquirer] [Job %s cancel·lat]", job_id)
        except ResourceConfigurationError as exc:
            await self._fail_job(job_id, resource_id, variant_id, "CONFIG_REQUIRED", str(exc))
        except ResourcePlanError as exc:
            await self._fail_job(job_id, resource_id, variant_id, "INVALID_PLAN", str(exc))
        except ResourceProcessingError as exc:
            await self._fail_job(job_id, resource_id, variant_id, "PROCESSING_ERROR", str(exc))
        except ResourceVerificationError as exc:
            await self._fail_job(job_id, resource_id, variant_id, "VERIFY_ERROR", str(exc))
        except AuthenticationRequiredError as exc:
            log.warning("MGP: [ParametricRasterAcquirer] Job %s missing CDSE auth", job_id)
            await self._fail_job(job_id, resource_id, variant_id, "AUTH_REQUIRED", str(exc))
        except Exception as exc:
            log.exception("MGP: [ParametricRasterAcquirer] [Job %s failed]", job_id)
            await self._fail_job(job_id, resource_id, variant_id, "NETWORK_ERROR", str(exc))

    async def _download_assets_in_parallel(
        self,
        *,
        session: aiohttp.ClientSession,
        job_id: str,
        resource_id: ResourceId,
        variant_id: VariantId,
        plan: ParametricDownloadPlan,
        final_paths: tuple[Path, ...],
        token: str,
        temp_dir: Path,
        active_tasks: Collection[str],
    ) -> int:
        """Download independent plan assets concurrently with aggregate progress."""

        downloaded_by_file = {
            asset.file_name: self._existing_bytes(temp_dir, asset.file_name, final_path)
            for asset, final_path in zip(plan.assets, final_paths, strict=True)
        }
        semaphore = asyncio.Semaphore(self._MAX_PARALLEL_ASSET_DOWNLOADS)
        total_by_file = {asset.file_name: asset.expected_bytes for asset in plan.assets}

        async def report_progress(file_name: str, downloaded: int) -> None:
            downloaded_by_file[file_name] = downloaded
            aggregate_downloaded = sum(downloaded_by_file.values())
            await self._send_snapshot(
                DownloadJobSnapshot(
                    job_id=job_id,
                    resource_id=resource_id,
                    variant_id=variant_id,
                    state=ResourceInstallState.DOWNLOADING,
                    downloaded_bytes=aggregate_downloaded,
                    total_bytes=plan.estimated_bytes,
                    progress=(
                        aggregate_downloaded / plan.estimated_bytes
                        if plan.estimated_bytes
                        else None
                    ),
                    current_file=file_name,
                    error_code=None,
                    error_message=None,
                    asset_progress=tuple(
                        DownloadAssetProgress(
                            file_name,
                            downloaded,
                            total_by_file[file_name],
                        )
                        for file_name, downloaded in downloaded_by_file.items()
                    ),
                )
            )

        async def download(asset, final_path: Path) -> None:
            if (
                final_path.is_file()
                or final_path.is_dir()
                or final_path.with_name(f"{final_path.name}.zip").is_file()
            ):
                return
            async with semaphore:
                await self._download_asset(
                    session=session,
                    job_id=job_id,
                    resource_id=resource_id,
                    variant_id=variant_id,
                    url=asset.download_url,
                    file_name=asset.file_name,
                    requires_authentication=asset.requires_authentication,
                    token=token,
                    total_downloaded=downloaded_by_file[asset.file_name],
                    overall_total_bytes=plan.estimated_bytes,
                    temp_dir=temp_dir,
                    final_path=final_path,
                    active_tasks=active_tasks,
                    progress_reporter=report_progress,
                )

        await asyncio.gather(
            *(download(asset, final_path) for asset, final_path in zip(plan.assets, final_paths, strict=True))
        )
        return sum(downloaded_by_file.values())

    @staticmethod
    def _existing_bytes(temp_dir: Path, file_name: str, final_path: Path) -> int:
        if final_path.is_file():
            return final_path.stat().st_size
        zip_cand = final_path.with_name(f"{final_path.name}.zip")
        if zip_cand.is_file():
            return zip_cand.stat().st_size
        if final_path.is_dir():
            return sum(p.stat().st_size for p in final_path.rglob("*") if p.is_file())
        partial = temp_dir / f"{file_name}.part"
        return partial.stat().st_size if partial.exists() else 0

    async def _verify_assets(
        self,
        plan: ParametricDownloadPlan,
        final_paths: tuple[Path, ...],
    ) -> dict[str, str]:
        hashes: dict[str, str] = {}
        for asset, final_path in zip(plan.assets, final_paths, strict=True):
            target_path = final_path
            if not target_path.exists():
                zip_cand = final_path.with_name(f"{final_path.name}.zip")
                if zip_cand.exists():
                    target_path = zip_cand
                elif final_path.is_dir():
                    # For directories, compute hash of inner files
                    hashes[asset.file_name] = "extracted"
                    continue
            actual_size = target_path.stat().st_size
            if asset.expected_bytes is not None and actual_size != asset.expected_bytes:
                raise ResourceVerificationError(
                    f"Size mismatch for {asset.file_name}: expected "
                    f"{asset.expected_bytes}, got {actual_size}"
                )
            hashes[asset.file_name] = await self._hash_file(target_path, "sha256")
            if asset.checksum_algorithm and asset.checksum_value:
                algo = asset.checksum_algorithm.lower()
                if algo != "etag":
                    calculated = await self._hash_file(target_path, asset.checksum_algorithm)
                    if calculated.lower() != asset.checksum_value.lower():
                        raise ResourceVerificationError(
                            f"Checksum mismatch for {asset.file_name}"
                        )
        return hashes

    @staticmethod
    async def _extract_downloaded_archives(
        final_paths: tuple[Path, ...],
    ) -> tuple[Path, ...]:
        unpacked: list[Path] = []
        for final_path in final_paths:
            if not final_path.exists():
                zip_candidate = final_path.with_name(f"{final_path.name}.zip")
                if zip_candidate.is_file() and zipfile.is_zipfile(zip_candidate):
                    unpacked.extend(
                        await asyncio.to_thread(
                            safe_extract_zip,
                            zip_candidate,
                            final_path,
                        )
                    )
                    continue
                if final_path.is_dir():
                    unpacked.extend(path for path in final_path.rglob("*") if path.is_file())
                    continue
            if final_path.is_file() and zipfile.is_zipfile(final_path):
                if final_path.suffix.lower() == ".zip":
                    archive_path = final_path
                    dest_path = final_path.with_suffix("")
                else:
                    archive_path = final_path.with_name(f"{final_path.name}.zip")
                    final_path.rename(archive_path)
                    dest_path = final_path
                unpacked.extend(
                    await asyncio.to_thread(
                        safe_extract_zip,
                        archive_path,
                        dest_path,
                    )
                )
            elif final_path.is_dir():
                unpacked.extend(path for path in final_path.rglob("*") if path.is_file())
            else:
                unpacked.append(final_path)
        return tuple(unpacked)

    async def _download_asset(
        self,
        *,
        session: aiohttp.ClientSession,
        job_id: str,
        resource_id: ResourceId,
        variant_id: VariantId,
        url: str,
        file_name: str,
        requires_authentication: bool,
        token: str,
        total_downloaded: int,
        overall_total_bytes: int | None,
        temp_dir: Path,
        final_path: Path,
        active_tasks: Collection[str],
        progress_reporter: Callable[[str, int], Awaitable[None]] | None = None,
    ) -> int:
        temp_path = temp_dir / f"{file_name}.part"
        existing_bytes = temp_path.stat().st_size if temp_path.exists() else 0
        for attempt in range(3):
            headers: dict[str, str] = {}
            if requires_authentication:
                headers["Authorization"] = f"Bearer {token}"
            if existing_bytes:
                headers["Range"] = f"bytes={existing_bytes}-"
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200 and existing_bytes:
                        total_downloaded -= existing_bytes
                        existing_bytes = 0
                        if progress_reporter is not None:
                            await progress_reporter(file_name, total_downloaded)
                    elif response.status == 401 and requires_authentication:
                        if hasattr(self, "_auth_coordinator") and self._auth_coordinator:
                            self._auth_coordinator.invalidate_session()
                            token = await self._auth_coordinator.get_valid_token(interactive=True)
                        raise aiohttp.ClientResponseError(
                            response.request_info,
                            response.history,
                            status=response.status,
                            message="Token expired, retrying",
                            headers=response.headers,
                        )
                    elif response.status not in (200, 206):
                        raise aiohttp.ClientResponseError(
                            response.request_info,
                            response.history,
                            status=response.status,
                            message=response.reason or "HTTP download failed",
                            headers=response.headers,
                        )
                    if response.content_type == "text/html":
                        raise ResourceVerificationError(
                            f"Unexpected HTML response for {file_name}"
                        )
                    mode = "ab" if existing_bytes else "wb"
                    with temp_path.open(mode) as output:
                        async for chunk in response.content.iter_chunked(64 * 1024):
                            if job_id not in active_tasks:
                                return total_downloaded
                            output.write(chunk)
                            total_downloaded += len(chunk)
                            if progress_reporter is not None:
                                await progress_reporter(file_name, total_downloaded)
                            else:
                                await self._send_snapshot(
                                    DownloadJobSnapshot(
                                        job_id=job_id,
                                        resource_id=resource_id,
                                        variant_id=variant_id,
                                        state=ResourceInstallState.DOWNLOADING,
                                        downloaded_bytes=total_downloaded,
                                        total_bytes=overall_total_bytes,
                                        progress=(
                                            total_downloaded / overall_total_bytes
                                            if overall_total_bytes
                                            else None
                                        ),
                                        current_file=file_name,
                                        error_code=None,
                                        error_message=None,
                                    )
                                )
                temp_path.replace(final_path)
                return total_downloaded
            except ResourceVerificationError:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt == 2:
                    raise
                await asyncio.sleep(0.25 * (2**attempt))
                existing_bytes = temp_path.stat().st_size if temp_path.exists() else 0
        raise RuntimeError("Download retry loop exhausted")
