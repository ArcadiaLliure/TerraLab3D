"""Transactional local raster imports; never represented as downloads."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from threading import RLock
from typing import Any, Callable

from terralab3d.application.ports.persistence import (
    DataSourceRepositoryPort,
    ResourceCatalogWriterPort,
    ResourceInstallationWriterPort,
)
from terralab3d.application.ports.raster import RasterReaderPort, TextRasterMaterializerPort
from terralab3d.application.ports.categorical_raster import CategoricalRasterPort
from terralab3d.application.ports.classification_schemes import (
    ClassificationSchemeRegistryPort,
    UserClassificationSchemeWriterPort,
)
from terralab3d.application.categorical_imports import (
    categorical_analysis_payload,
    confirmed_scheme_and_codes,
    scheme_catalog_payload,
)
from terralab3d.domain.elevation.models import ElevationRasterSource, VerticalUnit
from terralab3d.domain.identifiers import ResourceId, VariantId
from terralab3d.domain.raster.models import (
    RasterDatasetError,
    RasterDatasetSelection,
    RasterMetadataOverride,
    TextRasterOptions,
)
from terralab3d.domain.surface.categorical import (
    CategoricalEncoding,
    CategoricalRasterAnalysis,
    CategoricalValueCount,
)
from terralab3d.domain.surface.tlst import TlstValidationError
from terralab3d.domain.resources.models import (
    AcquisitionKind,
    ResourceCategory,
    ResourceDescriptor,
    ResourceDomain,
    ResourceInstallState,
    ResourceVariant,
)
class RasterImportError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RasterImportSession:
    import_id: str
    ownership: str
    name: str
    staging_dir: Path
    external_path: str | None
    file_count: int
    state: str
    files: tuple[dict[str, Any], ...]
    inspection: dict[str, Any] | None
    semantic_kind: str = "elevation"


class RasterImportService:
    """Coordinates staging, inspection and atomic registration boundaries."""

    def __init__(
        self,
        raster_reader: RasterReaderPort,
        text_materializer: TextRasterMaterializerPort,
        data_sources: DataSourceRepositoryPort,
        catalog: ResourceCatalogWriterPort,
        installations: ResourceInstallationWriterPort,
        *,
        data_root: Path,
        activation_callback: Callable[[], None] | None = None,
        categorical_raster: CategoricalRasterPort | None = None,
        scheme_registry: ClassificationSchemeRegistryPort | None = None,
        user_schemes: UserClassificationSchemeWriterPort | None = None,
        categorical_activation_callback: Callable[[], None] | None = None,
        progress_publisher: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._reader = raster_reader
        self._text_materializer = text_materializer
        self._data_sources = data_sources
        self._catalog = catalog
        self._installations = installations
        self._data_root = data_root.resolve(strict=False)
        self._staging_root = self._data_root / "state" / "raster-imports"
        self._elevation_library_root = (
            self._data_root / "data" / "earth" / "elevation" / "imports"
        )
        self._categorical_library_root = (
            self._data_root / "data" / "earth" / "categorical" / "imports"
        )
        self._cache_root = self._data_root / "cache" / "raster-imports"
        self._staging_root.mkdir(parents=True, exist_ok=True)
        self._elevation_library_root.mkdir(parents=True, exist_ok=True)
        self._categorical_library_root.mkdir(parents=True, exist_ok=True)
        self._cache_root.mkdir(parents=True, exist_ok=True)
        self._activation_callback = activation_callback
        self._categorical_raster = categorical_raster
        self._scheme_registry = scheme_registry
        self._user_schemes = user_schemes
        self._categorical_activation_callback = categorical_activation_callback
        self._progress_publisher = progress_publisher
        self._lock = RLock()

    def create(
        self,
        *,
        ownership: str = "managed",
        name: str = "",
        external_path: str | None = None,
        file_count: int = 1,
        semantic_kind: str = "elevation",
    ) -> RasterImportSession:
        if ownership not in {"managed", "external"}:
            raise RasterImportError("Ownership must be managed or external")
        if file_count < 1:
            raise RasterImportError("Import file count must be positive")
        if semantic_kind not in {"elevation", "categorical"}:
            raise RasterImportError("Raster semantics must be elevation or categorical")
        if semantic_kind == "categorical" and (
            self._categorical_raster is None
            or self._scheme_registry is None
            or self._user_schemes is None
        ):
            raise RasterImportError("Categorical import is not configured")
        if ownership == "external":
            candidate = Path(external_path or "")
            if not candidate.is_absolute():
                raise RasterImportError("External imports require an absolute backend path")
        import_id = uuid.uuid4().hex
        staging = self._staging_root / import_id
        (staging / "files").mkdir(parents=True)
        payload = {
            "importId": import_id,
            "ownership": ownership,
            "name": name.strip(),
            "externalPath": external_path,
            "fileCount": int(file_count),
            "state": "created",
            "files": [],
            "inspection": None,
            "semanticKind": semantic_kind,
            "createdAt": _utc_now(),
        }
        self._write_manifest(staging, payload)
        return _session(staging, payload)

    def upload_destination(self, import_id: str, ordinal: int, relative_path: str) -> Path:
        payload, staging = self._load(import_id)
        if payload["ownership"] != "managed":
            raise RasterImportError("External imports do not accept uploaded files")
        if ordinal < 0 or ordinal >= int(payload["fileCount"]):
            raise RasterImportError("Upload ordinal is outside the declared bundle")
        relative = _safe_relative_path(relative_path)
        destination = (staging / "files" / Path(*relative.parts)).resolve(strict=False)
        files_root = (staging / "files").resolve(strict=False)
        if not destination.is_relative_to(files_root):
            raise RasterImportError("Upload path escapes the import bundle")
        destination.parent.mkdir(parents=True, exist_ok=True)
        return destination

    def finish_upload(
        self,
        import_id: str,
        ordinal: int,
        relative_path: str,
        byte_size: int,
        sha256: str,
    ) -> RasterImportSession:
        with self._lock:
            payload, staging = self._load(import_id)
            relative = _safe_relative_path(relative_path).as_posix()
            files = [item for item in payload.get("files", []) if int(item["ordinal"]) != ordinal]
            files.append({
                "ordinal": ordinal,
                "relativePath": relative,
                "byteSize": int(byte_size),
                "sha256": sha256,
            })
            payload["files"] = sorted(files, key=lambda item: int(item["ordinal"]))
            payload["state"] = "uploaded"
            self._write_manifest(staging, payload)
            return _session(staging, payload)

    def inspect(self, import_id: str, request: dict[str, Any]) -> dict[str, Any]:
        payload, staging = self._load(import_id)
        selected_path = self._selected_path(payload, staging, request)
        text_options_payload = request.get("textOptions")
        inspected_path = selected_path
        try:
            descriptor = self._reader.inspect(str(selected_path), subdataset=request.get("subdataset"))
        except RasterDatasetError:
            if not isinstance(text_options_payload, dict):
                raise
            options = _text_options(text_options_payload)
            inspected_path = self._text_materializer.materialize(
                selected_path,
                self._cache_root / import_id,
                options,
            )
            descriptor = self._reader.inspect(str(inspected_path))
        result = _descriptor_dict(descriptor)
        result["selectedPath"] = str(selected_path)
        result["rasterPath"] = str(inspected_path)
        semantic_kind = str(payload.get("semanticKind", "elevation"))
        if semantic_kind == "categorical":
            result["metadataSuggestions"] = self._categorical_inspection(
                import_id,
                descriptor,
                inspected_path,
                request,
            )
            analysis = result["metadataSuggestions"].pop("analysis", None)
            if analysis is not None:
                result["categoricalAnalysis"] = analysis
        else:
            result["metadataSuggestions"] = {
                "verticalUnit": _suggest_vertical_unit(descriptor.bands[0].unit) if descriptor.bands else None,
                "requiresUnitConfirmation": True,
                "requiresBandSelection": len(descriptor.bands) != 1,
                "requiresSubdatasetSelection": bool(descriptor.subdatasets) and request.get("subdataset") is None,
            }
        payload["inspection"] = {**result, "request": request}
        payload["state"] = "inspected"
        self._write_manifest(staging, payload)
        return result

    def _publish_progress(self, import_id: str, fraction: float, message: str) -> None:
        if self._progress_publisher is not None:
            self._progress_publisher({
                "type": "operation_progressed",
                "operationId": import_id,
                "progressFraction": fraction,
                "messageKey": message,
            })

    def _categorical_inspection(
        self,
        import_id: str,
        descriptor: Any,
        inspected_path: Path,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        requires_subdataset = bool(descriptor.subdatasets) and request.get("subdataset") is None
        if requires_subdataset or not descriptor.bands:
            return {
                "requiresSubdatasetSelection": requires_subdataset,
                "requiresCategoricalSelection": True,
                "suggestedEncoding": None,
            }
        suggested, suggested_bands = _suggest_categorical_encoding(descriptor)
        encoding_raw = request.get("categoricalEncoding") or suggested.value
        try:
            encoding = CategoricalEncoding(str(encoding_raw))
        except ValueError as exc:
            raise RasterImportError(f"Unsupported categorical encoding: {encoding_raw!r}") from exc
        raw_indices = request.get("bandIndices")
        band_indices = (
            tuple(int(value) for value in raw_indices)
            if isinstance(raw_indices, list)
            else suggested_bands
        )
        required_count = {
            CategoricalEncoding.INTEGER: 1,
            CategoricalEncoding.PALETTE: 1,
            CategoricalEncoding.RGB: 3,
            CategoricalEncoding.RGBA: 4,
        }[encoding]
        suggestions: dict[str, Any] = {
            "requiresSubdatasetSelection": False,
            "requiresCategoricalSelection": len(band_indices) != required_count,
            "suggestedEncoding": suggested.value,
            "suggestedBandIndices": list(suggested_bands),
            "encodingConfirmationRequired": True,
        }
        if len(band_indices) == required_count:
            assert self._categorical_raster is not None
            selection = RasterDatasetSelection(
                str(inspected_path),
                subdataset=request.get("subdataset"),
            )

            def progress(fraction: float) -> None:
                self._publish_progress(import_id, fraction, "inspect")

            analysis = self._categorical_raster.analyse(
                selection,
                encoding=encoding,
                band_indices=band_indices,
                progress_callback=progress,
            )
            assert self._scheme_registry is not None
            suggestions["analysis"] = categorical_analysis_payload(
                analysis,
                self._scheme_registry,
            )
        return suggestions

    def commit(self, import_id: str, confirmation: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            payload, staging = self._load(import_id)
            inspection = payload.get("inspection")
            if not isinstance(inspection, dict):
                raise RasterImportError("Inspect the raster before committing it")
            if str(payload.get("semanticKind", "elevation")) == "categorical":
                return self._commit_categorical(import_id, payload, staging, inspection, confirmation)
            if confirmation.get("unitConfirmed") is not True:
                raise RasterImportError("The vertical unit must be confirmed explicitly")
            unit = VerticalUnit(str(confirmation.get("verticalUnit", "")))
            custom_factor = confirmation.get("customUnitToMetre")
            source_id = str(
                payload.get("pendingSourceId")
                or f"elevation.imported.{uuid.uuid4().hex}"
            )
            resource_id = ResourceId(f"earth.{source_id}")
            variant_id = VariantId("local")
            name = str(confirmation.get("name") or payload.get("name") or "DEM importat").strip()
            if not name:
                raise RasterImportError("An imported elevation resource needs a name")
            ownership = str(payload["ownership"])
            old_order = tuple(
                str(value)
                for value in self._data_sources.snapshot()
                .get("selections", {}).get("elevation", {}).get("source_ids", [])
            )
            overrides = _metadata_overrides(confirmation.get("overrides"))
            band_index = (
                int(confirmation["bandIndex"])
                if confirmation.get("bandIndex") is not None else None
            )
            candidate_path = Path(str(inspection["rasterPath"])).resolve(strict=False)
            candidate_subdataset = confirmation.get("subdataset")
            pending_install_dir = Path(str(payload.get("pendingInstallDir") or ""))
            if (
                ownership == "managed"
                and payload.get("pendingSourceId") == source_id
                and pending_install_dir.is_dir()
                and not (staging / "files").exists()
            ):
                candidate_path = _relocate_inspected_path(
                    inspection,
                    staging,
                    pending_install_dir,
                )
                candidate_subdataset = _relocate_subdataset(
                    candidate_subdataset,
                    staging / "files",
                    pending_install_dir,
                )
            candidate_selection = RasterDatasetSelection(
                str(candidate_path),
                band_index=band_index,
                subdataset=candidate_subdataset,
                overrides=overrides,
            )
            # Validate every semantic choice before changing ownership or persistence.
            descriptor = self._reader.validate_selection(candidate_selection)
            if descriptor.crs is None:
                raise RasterImportError("Elevation import requires a CRS or an explicit CRS override")
            ElevationRasterSource(
                source_id=source_id,
                selection=candidate_selection,
                vertical_unit=unit,
                unit_confirmed=True,
                custom_unit_to_metre=float(custom_factor) if custom_factor is not None else None,
            )
            installed_dir: Path | None = None
            if ownership == "managed":
                installed_dir = self._elevation_library_root / source_id
                files_dir = staging / "files"
                if installed_dir.exists() and files_dir.exists():
                    raise RasterImportError("Managed elevation destination already exists")
                if not installed_dir.exists():
                    _validate_managed_vrts(files_dir)
                    payload["state"] = "committing"
                    payload["pendingSourceId"] = source_id
                    payload["pendingResourceId"] = str(resource_id)
                    payload["pendingInstallDir"] = str(installed_dir)
                    self._write_manifest(staging, payload)
                    os.replace(files_dir, installed_dir)
                payload["state"] = "consolidated"
                self._write_manifest(staging, payload)
                raster_path = _relocate_inspected_path(inspection, staging, installed_dir)
                selected_subdataset = _relocate_subdataset(
                    candidate_subdataset,
                    staging / "files",
                    installed_dir,
                )
            else:
                raster_path = Path(str(inspection["rasterPath"])).resolve(strict=False)
                selected_subdataset = candidate_subdataset
                if not raster_path.exists():
                    raise RasterImportError("The external raster is no longer accessible")

            selection = RasterDatasetSelection(
                str(raster_path),
                band_index=band_index,
                subdataset=selected_subdataset,
                overrides=overrides,
            )
            elevation_source = ElevationRasterSource(
                source_id=source_id,
                selection=selection,
                vertical_unit=unit,
                unit_confirmed=True,
                custom_unit_to_metre=float(custom_factor) if custom_factor is not None else None,
            )
            fingerprint = _source_fingerprint(raster_path, confirmation)
            source_record = _source_record(
                elevation_source,
                ownership=ownership,
                resource_id=str(resource_id),
                descriptor=descriptor,
                fingerprint=fingerprint,
            )
            descriptor_record = ResourceDescriptor(
                id=resource_id,
                name=name,
                description="Model digital d'elevació importat localment.",
                domain=ResourceDomain.EARTH,
                category=ResourceCategory.ELEVATION,
                provider="Importació local",
                acquisition_kind=(
                    AcquisitionKind.GENERATED_DATASET
                    if ownership == "managed"
                    else AcquisitionKind.EXTERNAL_FILE
                ),
                citation="",
                license="Definida per l'usuari",
                variants=(ResourceVariant(
                    id=variant_id,
                    title="Local",
                    format=descriptor.driver,
                    width=descriptor.width,
                    height=descriptor.height,
                    metadata=(("ownership", ownership), ("sourceId", source_id)),
                ),),
                metadata=(("ownership", ownership), ("sourceId", source_id)),
            )
            try:
                self._catalog.upsert(descriptor_record)
                self._installations.set_resource_state(
                    resource_id,
                    ResourceInstallState.READY,
                    variant_id,
                    resolved_path=str(installed_dir or raster_path),
                    downloaded_bytes=sum(int(item.get("byteSize", 0)) for item in payload.get("files", [])),
                    verified_at=_utc_now(),
                    manifest_data={
                        "ownership": ownership,
                        "sourcePath": str(raster_path),
                        "fingerprint": fingerprint,
                    },
                )
                order = self._data_sources.activate_elevation(source_record)
                self._publish_elevation_roles(order)
                if self._activation_callback is not None:
                    self._activation_callback()
            except Exception:
                self._data_sources.remove(source_id)
                self._data_sources.restore_elevation_order(old_order)
                self._publish_elevation_roles(old_order)
                self._installations.remove_resource_state(resource_id, variant_id)
                self._catalog.remove(resource_id)
                if installed_dir is not None and installed_dir.is_dir():
                    shutil.rmtree(installed_dir)
                raise
            payload["state"] = "committed"
            payload["resourceId"] = str(resource_id)
            payload["sourceId"] = source_id
            payload["committedAt"] = _utc_now()
            self._write_manifest(staging, payload)
            shutil.rmtree(staging, ignore_errors=True)
            shutil.rmtree(self._cache_root / import_id, ignore_errors=True)
            return {
                "resourceId": str(resource_id),
                "sourceId": source_id,
                "active": True,
                "ownership": ownership,
                "fallbackSourceIds": list(order[1:]),
                "fingerprint": fingerprint,
            }

    def _commit_categorical(
        self,
        import_id: str,
        payload: dict[str, Any],
        staging: Path,
        inspection: dict[str, Any],
        confirmation: dict[str, Any],
    ) -> dict[str, Any]:
        if self._categorical_raster is None or self._scheme_registry is None:
            raise RasterImportError("Categorical import is not configured")
        raw_analysis = inspection.get("categoricalAnalysis")
        if not isinstance(raw_analysis, dict):
            raise RasterImportError(
                "Inspect the categorical encoding and bands before committing"
            )
        analysis = _categorical_analysis_from_payload(raw_analysis)
        try:
            scheme, code_by_value, created_scheme = confirmed_scheme_and_codes(
                analysis,
                confirmation,
                self._scheme_registry,
            )
        except (TlstValidationError, ValueError, KeyError) as exc:
            raise RasterImportError(str(exc)) from exc

        source_id = str(
            payload.get("pendingSourceId")
            or f"land_cover.imported.{uuid.uuid4().hex}"
        )
        resource_id = ResourceId(f"earth.{source_id}")
        payload.update({
            "state": "committing",
            "pendingSourceId": source_id,
            "pendingResourceId": str(resource_id),
        })
        self._write_manifest(staging, payload)
        variant_id = VariantId("local")
        name = str(
            confirmation.get("name") or payload.get("name") or "Cobertura importada"
        ).strip()
        if not name:
            raise RasterImportError("An imported categorical resource needs a name")
        ownership = str(payload["ownership"])
        old_source_id = self._data_sources.active_land_cover_source_id()
        overrides = _metadata_overrides(confirmation.get("overrides"))
        source_path = Path(str(inspection["rasterPath"])).resolve(strict=False)
        selected_subdataset = confirmation.get("subdataset")
        pending_install_dir = Path(str(payload.get("pendingInstallDir") or ""))
        recovering_managed = (
            ownership == "managed"
            and pending_install_dir.is_dir()
            and not (staging / "files").exists()
        )
        if recovering_managed:
            source_path = _relocate_inspected_path(
                inspection, staging, pending_install_dir,
            )
            selected_subdataset = _relocate_subdataset(
                selected_subdataset, staging / "files", pending_install_dir,
            )
        source_selection = RasterDatasetSelection(
            str(source_path),
            band_index=analysis.band_indices[0],
            subdataset=selected_subdataset,
            overrides=overrides,
        )
        descriptor = self._reader.validate_selection(source_selection)
        if descriptor.crs is None:
            raise RasterImportError(
                "Categorical import requires a CRS or an explicit CRS override"
            )

        installed_index = pending_install_dir / "derived" / "categorical-index.tif"
        provisional = self._cache_root / str(payload["importId"]) / "categorical-index.tif"
        if not (recovering_managed and installed_index.is_file()):
            def progress(fraction: float) -> None:
                self._publish_progress(import_id, fraction, "commit")

            self._categorical_raster.materialize_indexed(
                RasterDatasetSelection(
                    str(source_path),
                    subdataset=selected_subdataset,
                    overrides=overrides,
                ),
                provisional,
                encoding=analysis.encoding,
                band_indices=analysis.band_indices,
                code_by_source_value=code_by_value,
                progress_callback=progress,
            )
        # Windows does not allow the managed bundle to move while GDAL keeps a
        # window-read handle open in the reader's bounded LRU.
        self._reader.release(RasterDatasetSelection(
            str(source_path), subdataset=selected_subdataset,
        ))

        installed_dir: Path | None = None
        if ownership == "managed":
            installed_dir = (
                pending_install_dir
                if recovering_managed else self._categorical_library_root / source_id
            )
            files_dir = staging / "files"
            if installed_dir.exists() and not recovering_managed:
                raise RasterImportError("Managed categorical destination already exists")
            if not recovering_managed:
                _validate_managed_vrts(files_dir)
                payload["pendingInstallDir"] = str(installed_dir)
                self._write_manifest(staging, payload)
                os.replace(files_dir, installed_dir)
            derived_dir = installed_dir / "derived"
            derived_dir.mkdir(exist_ok=True)
            indexed_path = derived_dir / "categorical-index.tif"
            if not indexed_path.is_file():
                os.replace(provisional, indexed_path)
            original_path = _relocate_selected_path(inspection, staging, installed_dir)
        else:
            original_path = Path(str(inspection["selectedPath"])).resolve(strict=False)
            if not original_path.exists():
                raise RasterImportError("The external categorical raster is no longer accessible")
            derived_dir = self._data_root / "cache" / "categorical-sources" / source_id
            derived_dir.mkdir(parents=True, exist_ok=True)
            indexed_path = derived_dir / "categorical-index.tif"
            if provisional.is_file():
                os.replace(provisional, indexed_path)

        indexed_descriptor = self._reader.inspect(str(indexed_path))
        fingerprint = _source_fingerprint(original_path, confirmation)
        source_record = {
            "id": source_id,
            "display_name": name,
            "layer_type": "land_cover_categorical",
            "enabled": True,
            "valid": True,
            "resource_id": str(resource_id),
            "path": str(indexed_path),
            "original_path": str(original_path),
            "ownership": ownership,
            "scheme_key": scheme.scheme_key,
            "scheme_version": scheme.scheme_version,
            "mapping_revision": scheme.mapping_revision,
            "source_dtype": analysis.source_dtype,
            "payload_dtype": "uint16",
            "categorical_encoding": analysis.encoding.value,
            "band_indices": list(analysis.band_indices),
            "resolution_m": max(indexed_descriptor.resolution),
            "coverage": list(indexed_descriptor.bounds),
            "driver": descriptor.driver,
            "fingerprint": fingerprint,
        }
        descriptor_record = ResourceDescriptor(
            id=resource_id,
            name=name,
            description="Cobertura categòrica importada i interpretada amb TLST 1.0.",
            domain=ResourceDomain.EARTH,
            category=ResourceCategory.LAND_COVER,
            provider="Importació local",
            acquisition_kind=(
                AcquisitionKind.GENERATED_DATASET
                if ownership == "managed" else AcquisitionKind.EXTERNAL_FILE
            ),
            citation="",
            license="Definida per l'usuari",
            variants=(ResourceVariant(
                id=variant_id,
                title="Local",
                format=descriptor.driver,
                width=descriptor.width,
                height=descriptor.height,
                metadata=(
                    ("ownership", ownership),
                    ("sourceId", source_id),
                    ("schemeKey", scheme.scheme_key),
                    ("schemeVersion", scheme.scheme_version),
                    ("mappingRevision", scheme.mapping_revision),
                ),
            ),),
            metadata=(
                ("ownership", ownership),
                ("sourceId", source_id),
                ("active", True),
                ("schemeKey", scheme.scheme_key),
                ("schemeVersion", scheme.scheme_version),
                ("mappingRevision", scheme.mapping_revision),
            ),
        )
        try:
            if created_scheme:
                assert self._user_schemes is not None
                self._user_schemes.upsert(scheme)
            self._catalog.upsert(descriptor_record)
            self._installations.set_resource_state(
                resource_id,
                ResourceInstallState.READY,
                variant_id,
                resolved_path=str(installed_dir or original_path),
                downloaded_bytes=sum(
                    int(item.get("byteSize", 0)) for item in payload.get("files", [])
                ),
                verified_at=_utc_now(),
                manifest_data={
                    "ownership": ownership,
                    "sourcePath": str(original_path),
                    "derivedPath": str(indexed_path),
                    "fingerprint": fingerprint,
                    "schemeKey": scheme.scheme_key,
                    "schemeVersion": scheme.scheme_version,
                    "mappingRevision": scheme.mapping_revision,
                },
            )
            self._data_sources.activate_land_cover(source_record)
            self._publish_land_cover_role(source_id)
            if self._categorical_activation_callback is not None:
                self._categorical_activation_callback()
        except Exception:
            self._data_sources.remove(source_id)
            self._data_sources.restore_land_cover_source(old_source_id)
            self._publish_land_cover_role(old_source_id)
            self._installations.remove_resource_state(resource_id, variant_id)
            self._catalog.remove(resource_id)
            target = installed_dir or indexed_path.parent
            if target.is_dir():
                shutil.rmtree(target)
            raise

        payload.update({
            "state": "committed",
            "resourceId": str(resource_id),
            "sourceId": source_id,
            "committedAt": _utc_now(),
        })
        self._write_manifest(staging, payload)
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(self._cache_root / str(payload["importId"]), ignore_errors=True)
        return {
            "resourceId": str(resource_id),
            "sourceId": source_id,
            "active": True,
            "ownership": ownership,
            "schemeKey": scheme.scheme_key,
            "schemeVersion": scheme.scheme_version,
            "mappingRevision": scheme.mapping_revision,
            "fingerprint": fingerprint,
        }

    def cancel(self, import_id: str) -> None:
        _, staging = self._load(import_id)
        shutil.rmtree(staging)
        shutil.rmtree(self._cache_root / import_id, ignore_errors=True)

    def recoverable_sessions(self) -> tuple[RasterImportSession, ...]:
        sessions: list[RasterImportSession] = []
        for manifest in sorted(self._staging_root.glob("*/session.json")):
            try:
                payload = json.loads(manifest.read_text(encoding="utf-8"))
                sessions.append(_session(manifest.parent, payload))
            except (OSError, ValueError, TypeError):
                continue
        return tuple(sessions)

    def classification_scheme_catalog(self) -> dict[str, Any]:
        if self._scheme_registry is None:
            raise RasterImportError("Categorical import is not configured")
        return scheme_catalog_payload(self._scheme_registry)

    def remove_resource(self, source_id: str) -> None:
        record = self._data_sources.remove(source_id)
        if record is None:
            return
        resource_id = ResourceId(str(record["resource_id"]))
        ownership = str(record.get("ownership", "external"))
        layer_type = str(record.get("layer_type", ""))
        library_root = (
            self._elevation_library_root
            if layer_type == "elevation" else self._categorical_library_root
        ).resolve(strict=False)
        if ownership == "managed":
            original = Path(str(record.get("original_path") or record["path"])).resolve(strict=False)
            relative = original.relative_to(library_root)
            target = library_root / relative.parts[0]
            if not target.is_relative_to(library_root) or target == library_root:
                raise RasterImportError("Refusing to remove a managed raster outside its library")
            if target.exists():
                shutil.rmtree(target)
        elif layer_type != "elevation":
            derived = Path(str(record.get("path", ""))).resolve(strict=False)
            cache_root = (self._data_root / "cache" / "categorical-sources").resolve(strict=False)
            target = derived.parent
            if target.is_relative_to(cache_root) and target != cache_root and target.exists():
                shutil.rmtree(target)
        self._installations.remove_resource_state(resource_id, VariantId("local"))
        self._catalog.remove(resource_id)
        if layer_type == "elevation":
            remaining_order = tuple(
                str(value)
                for value in self._data_sources.snapshot()
                .get("selections", {}).get("elevation", {}).get("source_ids", [])
            )
            self._publish_elevation_roles(remaining_order)
        else:
            self._publish_land_cover_role(
                self._data_sources.active_land_cover_source_id()
            )
        shutil.rmtree(self._cache_root / source_id, ignore_errors=True)
        if layer_type == "elevation" and self._activation_callback is not None:
            self._activation_callback()
        elif layer_type != "elevation" and self._categorical_activation_callback is not None:
            self._categorical_activation_callback()

    def _publish_elevation_roles(self, order: tuple[str, ...]) -> None:
        records = {
            str(item.get("id")): item
            for item in self._data_sources.snapshot().get("sources", [])
            if isinstance(item, dict) and item.get("layer_type") == "elevation"
        }
        for index, source_id in enumerate(order):
            record = records.get(source_id)
            if record is None or not record.get("resource_id"):
                continue
            resource_id = ResourceId(str(record["resource_id"]))
            descriptor = self._catalog.get_descriptor(resource_id)
            if descriptor is None:
                continue
            metadata = dict(descriptor.metadata)
            metadata.update({
                "ownership": str(record.get("ownership", "external")),
                "sourceId": source_id,
                "active": index == 0,
                "fallback": index > 0,
                "fallbackOrder": index,
            })
            self._catalog.upsert(replace(descriptor, metadata=tuple(metadata.items())))

    def _publish_land_cover_role(self, active_source_id: str | None) -> None:
        for record in self._data_sources.land_cover_records():
            source_id = str(record.get("id", ""))
            if not source_id or not record.get("resource_id"):
                continue
            resource_id = ResourceId(str(record["resource_id"]))
            descriptor = self._catalog.get_descriptor(resource_id)
            if descriptor is None:
                continue
            metadata = dict(descriptor.metadata)
            metadata.update({
                "ownership": str(record.get("ownership", "external")),
                "sourceId": source_id,
                "active": source_id == active_source_id,
                "fallback": False,
            })
            self._catalog.upsert(replace(descriptor, metadata=tuple(metadata.items())))

    def _selected_path(
        self,
        payload: dict[str, Any],
        staging: Path,
        request: dict[str, Any],
    ) -> Path:
        if payload["ownership"] == "external":
            path = Path(str(payload.get("externalPath") or ""))
            if not path.is_absolute() or not path.exists():
                raise RasterImportError("External raster path is not accessible")
            return path.resolve(strict=True)
        ordinal = int(request.get("fileOrdinal", 0))
        entry = next(
            (item for item in payload.get("files", []) if int(item["ordinal"]) == ordinal),
            None,
        )
        if entry is None:
            raise RasterImportError("Selected managed bundle file has not been uploaded")
        return self.upload_destination(import_id=payload["importId"], ordinal=ordinal, relative_path=entry["relativePath"])

    def _load(self, import_id: str) -> tuple[dict[str, Any], Path]:
        if not import_id or any(value not in "0123456789abcdef" for value in import_id):
            raise RasterImportError("Invalid raster import id")
        staging = (self._staging_root / import_id).resolve(strict=False)
        if not staging.is_relative_to(self._staging_root.resolve(strict=False)):
            raise RasterImportError("Invalid raster import path")
        manifest = staging / "session.json"
        if not manifest.is_file():
            raise RasterImportError("Raster import session does not exist")
        return json.loads(manifest.read_text(encoding="utf-8")), staging

    @staticmethod
    def _write_manifest(staging: Path, payload: dict[str, Any]) -> None:
        temp = staging / "session.json.tmp"
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        temp.replace(staging / "session.json")

def elevation_sources_from_repository(
    repository: DataSourceRepositoryPort,
) -> tuple[ElevationRasterSource, ...]:
    sources: list[ElevationRasterSource] = []
    for record in repository.elevation_records():
        if record.get("enabled", True) is False or record.get("valid", True) is False:
            continue
        path = Path(str(record.get("path", "")))
        if record.get("ownership") == "external" and not path.exists():
            continue
        override_payload = record.get("overrides")
        overrides = _metadata_overrides(override_payload) if isinstance(override_payload, dict) else None
        vertical_unit_raw = record.get("vertical_unit", "metre")
        try:
            vertical_unit = VerticalUnit(str(vertical_unit_raw))
        except ValueError:
            vertical_unit = VerticalUnit.METRE
        sources.append(ElevationRasterSource(
            source_id=str(record["id"]),
            selection=RasterDatasetSelection(
                str(path),
                band_index=int(record["band_index"]) if record.get("band_index") is not None else None,
                subdataset=record.get("subdataset"),
                overrides=overrides,
            ),
            vertical_unit=vertical_unit,
            unit_confirmed=bool(record.get("unit_confirmed", True)),
            custom_unit_to_metre=(
                float(record["custom_unit_to_metre"])
                if record.get("custom_unit_to_metre") is not None else None
            ),
        ))
    return tuple(sources)


def _safe_relative_path(value: str) -> PurePosixPath:
    normalized = str(value or "").replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise RasterImportError("Bundle paths must be safe relative paths")
    return path


def _session(staging: Path, payload: dict[str, Any]) -> RasterImportSession:
    return RasterImportSession(
        import_id=str(payload["importId"]),
        ownership=str(payload["ownership"]),
        name=str(payload.get("name", "")),
        staging_dir=staging,
        external_path=payload.get("externalPath"),
        file_count=int(payload["fileCount"]),
        state=str(payload["state"]),
        files=tuple(payload.get("files", [])),
        inspection=payload.get("inspection"),
        semantic_kind=str(payload.get("semanticKind", "elevation")),
    )


def _descriptor_dict(descriptor: Any) -> dict[str, Any]:
    return {
        "uri": descriptor.uri,
        "driver": descriptor.driver,
        "width": descriptor.width,
        "height": descriptor.height,
        "crs": descriptor.crs,
        "transform": list(descriptor.transform),
        "bounds": list(descriptor.bounds),
        "resolution": list(descriptor.resolution),
        "sourceDtype": descriptor.source_dtype,
        "subdatasets": list(descriptor.subdatasets),
        "bands": [
            {
                "index": band.index,
                "dtype": band.dtype,
                "description": band.description,
                "nodata": band.nodata,
                "scale": band.scale,
                "offset": band.offset,
                "unit": band.unit,
                "maskFlags": list(band.mask_flags),
                "overviews": list(band.overviews),
                "colorInterpretation": band.color_interpretation,
                "hasColorMap": bool(band.color_map),
            }
            for band in descriptor.bands
        ],
    }


def _suggest_categorical_encoding(descriptor: Any) -> tuple[CategoricalEncoding, tuple[int, ...]]:
    if len(descriptor.bands) == 1:
        encoding = (
            CategoricalEncoding.PALETTE
            if descriptor.bands[0].color_map else CategoricalEncoding.INTEGER
        )
        return encoding, (1,)
    interpretations = [
        str(band.color_interpretation or "").lower()
        for band in descriptor.bands
    ]
    by_interpretation = {
        name: index + 1 for index, name in enumerate(interpretations)
    }
    if all(name in by_interpretation for name in ("red", "green", "blue", "alpha")):
        return CategoricalEncoding.RGBA, tuple(
            by_interpretation[name] for name in ("red", "green", "blue", "alpha")
        )
    if all(name in by_interpretation for name in ("red", "green", "blue")):
        return CategoricalEncoding.RGB, tuple(
            by_interpretation[name] for name in ("red", "green", "blue")
        )
    return CategoricalEncoding.RGB, tuple(range(1, min(3, len(descriptor.bands)) + 1))


def _categorical_analysis_from_payload(payload: dict[str, Any]) -> CategoricalRasterAnalysis:
    raw_values = payload.get("values")
    if not isinstance(raw_values, list):
        raise RasterImportError("Stored categorical analysis is invalid")
    return CategoricalRasterAnalysis(
        encoding=CategoricalEncoding(str(payload["encoding"])),
        band_indices=tuple(int(value) for value in payload["bandIndices"]),
        source_dtype=str(payload["sourceDtype"]),
        values=tuple(
            CategoricalValueCount(
                source_value=item["sourceValue"],
                pixel_count=int(item["pixelCount"]),
                color_rgba=(
                    tuple(int(channel) for channel in item["colorRgba"])
                    if item.get("colorRgba") is not None else None
                ),
            )
            for item in raw_values
            if isinstance(item, dict)
        ),
        valid_pixels=int(payload["validPixels"]),
        invalid_pixels=int(payload["invalidPixels"]),
    )


def _text_options(payload: dict[str, Any]) -> TextRasterOptions:
    transform = payload.get("transform")
    return TextRasterOptions(
        layout=payload.get("layout"),
        delimiter=payload.get("delimiter"),
        has_header=payload.get("hasHeader"),
        crs=payload.get("crs"),
        transform=tuple(float(value) for value in transform) if transform is not None else None,
        nodata=payload.get("nodata"),
    )


def _metadata_overrides(payload: Any) -> RasterMetadataOverride | None:
    if not isinstance(payload, dict) or not payload:
        return None
    transform = payload.get("transform")
    bounds = payload.get("bounds")
    return RasterMetadataOverride(
        crs=payload.get("crs"),
        transform=tuple(float(value) for value in transform) if transform is not None else None,
        bounds=tuple(float(value) for value in bounds) if bounds is not None else None,
        nodata=payload.get("nodata"),
        nodata_is_set="nodata" in payload,
        provenance=str(payload.get("provenance") or "import-confirmation"),
    )


def _source_record(
    source: ElevationRasterSource,
    *,
    ownership: str,
    resource_id: str,
    descriptor: Any,
    fingerprint: str,
) -> dict[str, Any]:
    override = source.selection.overrides
    return {
        "id": source.source_id,
        "layer_type": "elevation",
        "enabled": True,
        "valid": True,
        "resource_id": resource_id,
        "path": source.selection.uri,
        "ownership": ownership,
        "band_index": source.selection.band_index,
        "subdataset": source.selection.subdataset,
        "vertical_unit": source.vertical_unit.value,
        "unit_confirmed": source.unit_confirmed,
        "custom_unit_to_metre": source.custom_unit_to_metre,
        "source_dtype": descriptor.source_dtype,
        "driver": descriptor.driver,
        "fingerprint": fingerprint,
        "overrides": ({
            "crs": override.crs,
            "transform": list(override.transform) if override.transform else None,
            "bounds": list(override.bounds) if override.bounds else None,
            **({"nodata": override.nodata} if override.nodata_is_set else {}),
            "provenance": override.provenance,
        } if override else None),
    }


def _suggest_vertical_unit(unit: str | None) -> str | None:
    normalized = (unit or "").strip().casefold()
    if normalized in {"m", "metre", "meter", "metres", "meters"}:
        return VerticalUnit.METRE.value
    if normalized in {"ft", "foot", "feet"}:
        return VerticalUnit.INTERNATIONAL_FOOT.value
    return None


def _source_fingerprint(path: Path, confirmation: dict[str, Any]) -> str:
    stat = path.stat()
    payload = (
        f"{path.resolve(strict=False)}|{stat.st_size}|{stat.st_mtime_ns}|"
        f"{json.dumps(confirmation, sort_keys=True, ensure_ascii=False)}"
    ).encode("utf-8")
    return hashlib.blake2b(payload, digest_size=20).hexdigest()


def _relocate_inspected_path(
    inspection: dict[str, Any],
    staging: Path,
    installed_dir: Path,
) -> Path:
    raster_path = Path(str(inspection["rasterPath"])).resolve(strict=False)
    files_root = (staging / "files").resolve(strict=False)
    if raster_path.is_relative_to(files_root):
        return installed_dir / raster_path.relative_to(files_root)
    if raster_path.is_relative_to((staging.parent.parent.parent / "cache").resolve(strict=False)):
        # Text materializations are derived but needed by the managed source.
        target = installed_dir / "materialized.tif"
        shutil.copy2(raster_path, target)
        return target
    raise RasterImportError("Inspected managed raster is outside its bundle/cache")


def _relocate_selected_path(
    inspection: dict[str, Any],
    staging: Path,
    installed_dir: Path,
) -> Path:
    selected_path = Path(str(inspection["selectedPath"])).resolve(strict=False)
    files_root = (staging / "files").resolve(strict=False)
    if not selected_path.is_relative_to(files_root):
        raise RasterImportError("Selected managed source is outside its bundle")
    return installed_dir / selected_path.relative_to(files_root)


def _relocate_subdataset(
    value: str | None,
    old_bundle: Path,
    new_bundle: Path,
) -> str | None:
    if value is None:
        return None
    old_variants = {
        str(old_bundle),
        str(old_bundle.resolve(strict=False)),
        str(old_bundle).replace("\\", "/"),
        str(old_bundle.resolve(strict=False)).replace("\\", "/"),
    }
    relocated = value
    for old in sorted(old_variants, key=len, reverse=True):
        relocated = relocated.replace(old, str(new_bundle))
    return relocated


def _validate_managed_vrts(bundle_root: Path) -> None:
    resolved_root = bundle_root.resolve(strict=False)
    for vrt in bundle_root.rglob("*.vrt"):
        try:
            root = ET.parse(vrt).getroot()
        except ET.ParseError as exc:
            raise RasterImportError(f"Invalid managed VRT: {vrt.name}") from exc
        for element in root.iter("SourceFilename"):
            value = (element.text or "").strip()
            if not value:
                continue
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = vrt.parent / candidate
            resolved = candidate.resolve(strict=False)
            if not resolved.is_relative_to(resolved_root):
                raise RasterImportError("A managed VRT cannot reference files outside its bundle")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
