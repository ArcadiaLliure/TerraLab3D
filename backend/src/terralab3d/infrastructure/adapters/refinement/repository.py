"""Atomic, versioned JSON persistence for refinement installations."""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from threading import RLock
from typing import Any

from terralab3d.domain.refinement.errors import RefinementPersistenceError
from terralab3d.domain.refinement.installations import (
    CoverageVerificationMethod,
    GeometryRecord,
    RefinementDataKind,
    RefinementInstallation,
    TechnicalResourceState,
)
from terralab3d.domain.refinement.licensing import LicenseMetadata
from terralab3d.domain.refinement.states import SpatialCoverageState
from terralab3d.infrastructure.app_paths import resolve_resource_state_dir


class JsonRefinementInstallationRepository:
    SCHEMA_VERSION = 1

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (resolve_resource_state_dir() / "refinement_installations.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._installations: dict[str, RefinementInstallation] = {}
        self.load()

    def load(self) -> None:
        with self._lock:
            if not self.path.exists():
                self._installations = {}
                self._write_atomic(self._installations)
                return
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                records, migrated = self._extract_records(payload)
                parsed = tuple(_installation_from_dict(record) for record in records)
                self._installations = {item.installation_id: item for item in parsed}
                if len(self._installations) != len(parsed):
                    raise RefinementPersistenceError("Duplicate refinement installation id")
                if migrated:
                    self._write_atomic(self._installations)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                raise RefinementPersistenceError(
                    f"Cannot load refinement installation state from {self.path}"
                ) from exc

    def list_installations(self) -> tuple[RefinementInstallation, ...]:
        with self._lock:
            return tuple(self._installations[key] for key in sorted(self._installations))

    def get(self, installation_id: str) -> RefinementInstallation | None:
        with self._lock:
            return self._installations.get(installation_id)

    def upsert(self, installation: RefinementInstallation) -> None:
        with self._lock:
            candidate = dict(self._installations)
            candidate[installation.installation_id] = installation
            self._write_atomic(candidate)
            self._installations = candidate

    def remove(self, installation_id: str) -> RefinementInstallation | None:
        with self._lock:
            current = self._installations.get(installation_id)
            if current is None:
                return None
            candidate = dict(self._installations)
            del candidate[installation_id]
            self._write_atomic(candidate)
            self._installations = candidate
            return current

    def save(self) -> None:
        with self._lock:
            self._write_atomic(self._installations)

    def _write_atomic(self, installations: dict[str, RefinementInstallation]) -> None:
        document = {
            "schemaVersion": self.SCHEMA_VERSION,
            "installations": [
                _installation_to_dict(installations[key])
                for key in sorted(installations)
            ],
        }
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(document, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            self._replace_atomic(temporary, self.path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise RefinementPersistenceError(
                f"Cannot persist refinement installation state to {self.path}"
            ) from exc

    @staticmethod
    def _replace_atomic(source: Path, destination: Path) -> None:
        source.replace(destination)

    @classmethod
    def _extract_records(cls, payload: object) -> tuple[list[dict[str, Any]], bool]:
        migrated = False
        if isinstance(payload, list):
            records = payload
            migrated = True
        elif isinstance(payload, dict):
            version = payload.get("schemaVersion", 0)
            if version == cls.SCHEMA_VERSION:
                records = payload.get("installations")
            elif version == 0:
                records = payload.get("records", payload.get("installations", []))
                migrated = True
            else:
                raise RefinementPersistenceError(
                    f"Unsupported refinement state schema version: {version!r}"
                )
        else:
            raise RefinementPersistenceError("Refinement state root must be an object")
        if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
            raise RefinementPersistenceError("Refinement state records must be objects")
        return records, migrated


def _geometry_to_dict(value: GeometryRecord | None) -> dict[str, object] | None:
    if value is None:
        return None
    return {"crs": value.crs, "geojson": dict(value.geojson)}


def _geometry_from_dict(value: object) -> GeometryRecord | None:
    if value is None:
        return None
    if not isinstance(value, dict) or not isinstance(value.get("geojson"), dict):
        raise RefinementPersistenceError("Invalid persisted refinement geometry")
    return GeometryRecord(crs=str(value["crs"]), geojson=value["geojson"])


def _license_to_dict(value: LicenseMetadata) -> dict[str, object]:
    return {
        "licenseId": value.license_id,
        "officialUrl": value.official_url,
        "attributionText": value.attribution_text,
        "citation": value.citation,
        "provider": value.provider,
        "product": value.product,
        "version": value.version,
        "checkedAt": value.checked_at.isoformat() if value.checked_at else None,
        "provenanceUrl": value.provenance_url,
        "assetFingerprints": list(value.asset_fingerprints),
        "commercialUse": value.commercial_use,
        "nonCommercial": value.non_commercial,
        "shareAlike": value.share_alike,
        "odbl": value.odbl,
        "derivedDatabaseShareAlike": value.derived_database_share_alike,
        "researchOnly": value.research_only,
        "attributionOnlyEquivalent": value.attribution_only_equivalent,
        "metadataComplete": value.metadata_complete,
        "upstreamLicenses": list(value.upstream_licenses),
        "upstreamSources": list(value.upstream_sources),
    }


def _license_from_dict(value: object) -> LicenseMetadata:
    if not isinstance(value, dict):
        raise RefinementPersistenceError("Invalid persisted license metadata")
    checked = value.get("checkedAt")
    return LicenseMetadata(
        license_id=str(value.get("licenseId", "")),
        official_url=str(value.get("officialUrl", "")),
        attribution_text=str(value.get("attributionText", "")),
        citation=str(value.get("citation", "")),
        provider=str(value.get("provider", "")),
        product=str(value.get("product", "")),
        version=str(value.get("version", "")),
        checked_at=date.fromisoformat(str(checked)) if checked else None,
        provenance_url=str(value.get("provenanceUrl", "")),
        asset_fingerprints=tuple(str(item) for item in value.get("assetFingerprints", [])),
        commercial_use=value.get("commercialUse"),
        non_commercial=bool(value.get("nonCommercial", False)),
        share_alike=bool(value.get("shareAlike", False)),
        odbl=bool(value.get("odbl", False)),
        derived_database_share_alike=bool(value.get("derivedDatabaseShareAlike", False)),
        research_only=bool(value.get("researchOnly", False)),
        attribution_only_equivalent=bool(value.get("attributionOnlyEquivalent", False)),
        metadata_complete=bool(value.get("metadataComplete", True)),
        upstream_licenses=tuple(str(item) for item in value.get("upstreamLicenses", [])),
        upstream_sources=tuple(str(item) for item in value.get("upstreamSources", [])),
    )


def _installation_to_dict(value: RefinementInstallation) -> dict[str, object]:
    return {
        "installationId": value.installation_id,
        "resourceId": value.resource_id,
        "variantId": value.variant_id,
        "provider": value.provider,
        "product": value.product,
        "version": value.version,
        "tlstNodes": list(value.tlst_nodes),
        "dataKind": value.data_kind.value,
        "localPath": value.local_path,
        "plannedGeometry": _geometry_to_dict(value.planned_geometry),
        "verifiedGeometry": _geometry_to_dict(value.verified_geometry),
        "originalCrs": value.original_crs,
        "createdAt": value.created_at.isoformat(),
        "installedAt": value.installed_at.isoformat() if value.installed_at else None,
        "technicalState": value.technical_state.value,
        "spatialState": value.spatial_state.value,
        "jobId": value.job_id,
        "license": _license_to_dict(value.license),
        "provenanceUrl": value.provenance_url,
        "fileFingerprints": list(value.file_fingerprints),
        "verificationMethod": (
            value.verification_method.value if value.verification_method else None
        ),
        "aoiId": value.aoi_id,
    }


def _installation_from_dict(value: dict[str, Any]) -> RefinementInstallation:
    planned = _geometry_from_dict(value.get("plannedGeometry"))
    if planned is None:
        raise RefinementPersistenceError("Persisted installation lacks planned geometry")
    installed_at = value.get("installedAt")
    method = value.get("verificationMethod")
    return RefinementInstallation(
        installation_id=str(value["installationId"]),
        resource_id=str(value["resourceId"]),
        variant_id=str(value["variantId"]),
        provider=str(value["provider"]),
        product=str(value["product"]),
        version=str(value["version"]),
        tlst_nodes=tuple(str(item) for item in value["tlstNodes"]),
        data_kind=RefinementDataKind(str(value["dataKind"])),
        local_path=str(value["localPath"]),
        planned_geometry=planned,
        verified_geometry=_geometry_from_dict(value.get("verifiedGeometry")),
        original_crs=str(value["originalCrs"]),
        created_at=datetime.fromisoformat(str(value["createdAt"])),
        installed_at=datetime.fromisoformat(str(installed_at)) if installed_at else None,
        technical_state=TechnicalResourceState(str(value["technicalState"])),
        spatial_state=SpatialCoverageState(str(value["spatialState"])),
        job_id=str(value["jobId"]) if value.get("jobId") else None,
        license=_license_from_dict(value["license"]),
        provenance_url=str(value["provenanceUrl"]),
        file_fingerprints=tuple(str(item) for item in value.get("fileFingerprints", [])),
        verification_method=CoverageVerificationMethod(str(method)) if method else None,
        aoi_id=str(value.get("aoiId", "default")),
    )
