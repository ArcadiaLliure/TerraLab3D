"""Immutable plans for parametric refinement downloads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Mapping

from .errors import RefinementValidationError


_PLAN_SCHEMA_VERSION = 3


@dataclass(frozen=True, slots=True)
class FrozenDownloadAsset:
    asset_id: str
    provider_id: str
    product: str
    version: str
    download_url: str
    file_name: str
    footprint: Mapping[str, object]
    order: int
    expected_bytes: int | None
    checksum_algorithm: str | None
    checksum_value: str | None
    license_id: str
    license_url: str
    attribution: str
    provenance_url: str
    requires_authentication: bool
    class_translation: Mapping[int, str]
    nodata_values: tuple[int, ...]
    qualifier_key: str | None

    def __post_init__(self) -> None:
        required = (
            self.asset_id,
            self.provider_id,
            self.product,
            self.version,
            self.download_url,
            self.file_name,
            self.license_id,
            self.license_url,
            self.attribution,
            self.provenance_url,
        )
        if any(not value.strip() for value in required) or self.order < 0:
            raise RefinementValidationError("Frozen download asset metadata is incomplete")
        if (
            PurePosixPath(self.file_name).name != self.file_name
            or PureWindowsPath(self.file_name).name != self.file_name
            or self.file_name in {".", ".."}
        ):
            raise RefinementValidationError("Frozen asset filename is unsafe")
        normalized = json.loads(json.dumps(dict(self.footprint)))
        object.__setattr__(self, "footprint", MappingProxyType(normalized))
        object.__setattr__(
            self,
            "class_translation",
            MappingProxyType(dict(self.class_translation)),
        )


@dataclass(frozen=True, slots=True)
class ParametricDownloadPlan:
    plan_id: str
    request_id: str
    revision: int
    category_keys: tuple[str, ...]
    product_ids: tuple[str, ...]
    aoi_geojson: Mapping[str, object]
    assets: tuple[FrozenDownloadAsset, ...]
    processing_options: Mapping[str, str | int | float | bool]
    estimated_bytes: int | None
    requires_large_download_confirmation: bool

    def __post_init__(self) -> None:
        if (
            not self.plan_id.strip()
            or not self.request_id.strip()
            or self.revision < 0
            or not self.category_keys
            or not self.product_ids
            or not self.assets
        ):
            raise RefinementValidationError("Parametric download plan is incomplete")
        orders = [asset.order for asset in self.assets]
        if orders != sorted(orders) or len({asset.asset_id for asset in self.assets}) != len(self.assets):
            raise RefinementValidationError("Plan assets must be uniquely and deterministically ordered")
        normalized_aoi = json.loads(json.dumps(dict(self.aoi_geojson)))
        object.__setattr__(self, "aoi_geojson", MappingProxyType(normalized_aoi))
        object.__setattr__(
            self,
            "processing_options",
            MappingProxyType(dict(self.processing_options)),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    def to_dict(self) -> dict[str, object]:
        return {
            "schemaVersion": _PLAN_SCHEMA_VERSION,
            "planId": self.plan_id,
            "requestId": self.request_id,
            "revision": self.revision,
            "categoryKeys": list(self.category_keys),
            "productIds": list(self.product_ids),
            "aoi": dict(self.aoi_geojson),
            "assets": [_asset_to_dict(asset) for asset in self.assets],
            "processingOptions": dict(self.processing_options),
            "estimatedBytes": self.estimated_bytes,
            "requiresLargeDownloadConfirmation": self.requires_large_download_confirmation,
        }

    @classmethod
    def from_json(cls, value: str) -> ParametricDownloadPlan:
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise RefinementValidationError("Parametric plan is not valid JSON") from exc
        if not isinstance(payload, dict) or payload.get("schemaVersion") not in {1, 2, 3}:
            raise RefinementValidationError("Unsupported parametric plan schema")
        assets = payload.get("assets")
        if not isinstance(assets, list):
            raise RefinementValidationError("Parametric plan assets must be an array")
        aoi = payload.get("aoi")
        options = payload.get("processingOptions", {})
        if not isinstance(aoi, dict) or not isinstance(options, dict):
            raise RefinementValidationError("Parametric plan AOI or options are invalid")
        product_ids = payload.get("productIds")
        if not isinstance(product_ids, list):
            product_ids = [
                item.get("assetId")
                for item in assets
                if isinstance(item, dict) and item.get("assetId")
            ]
        return cls(
            plan_id=str(payload.get("planId", "")),
            request_id=str(payload.get("requestId", "")),
            revision=int(payload.get("revision", -1)),
            category_keys=tuple(str(item) for item in payload.get("categoryKeys", [])),
            product_ids=tuple(dict.fromkeys(str(item) for item in product_ids)),
            aoi_geojson=aoi,
            assets=tuple(_asset_from_dict(item) for item in assets),
            processing_options={
                str(key): value
                for key, value in options.items()
                if isinstance(value, (str, int, float, bool))
            },
            estimated_bytes=(
                int(payload["estimatedBytes"])
                if payload.get("estimatedBytes") is not None
                else None
            ),
            requires_large_download_confirmation=bool(
                payload.get("requiresLargeDownloadConfirmation", False)
            ),
        )


def _asset_to_dict(asset: FrozenDownloadAsset) -> dict[str, object]:
    return {
        "assetId": asset.asset_id,
        "providerId": asset.provider_id,
        "product": asset.product,
        "version": asset.version,
        "downloadUrl": asset.download_url,
        "fileName": asset.file_name,
        "footprint": dict(asset.footprint),
        "order": asset.order,
        "expectedBytes": asset.expected_bytes,
        "checksumAlgorithm": asset.checksum_algorithm,
        "checksumValue": asset.checksum_value,
        "licenseId": asset.license_id,
        "licenseUrl": asset.license_url,
        "attribution": asset.attribution,
        "provenanceUrl": asset.provenance_url,
        "requiresAuthentication": asset.requires_authentication,
        "classTranslation": {
            str(source_value): category_key
            for source_value, category_key in asset.class_translation.items()
        },
        "nodataValues": list(asset.nodata_values),
        "qualifierKey": asset.qualifier_key,
    }


def _asset_from_dict(value: object) -> FrozenDownloadAsset:
    if not isinstance(value, dict) or not isinstance(value.get("footprint"), dict):
        raise RefinementValidationError("Invalid frozen asset")
    translation = value.get("classTranslation", {})
    if not isinstance(translation, dict):
        raise RefinementValidationError("Invalid frozen asset translation")
    return FrozenDownloadAsset(
        asset_id=str(value.get("assetId", "")),
        provider_id=str(value.get("providerId", "")),
        product=str(value.get("product", "")),
        version=str(value.get("version", "")),
        download_url=str(value.get("downloadUrl", "")),
        file_name=str(value.get("fileName", "")),
        footprint=value["footprint"],
        order=int(value.get("order", -1)),
        expected_bytes=(
            int(value["expectedBytes"])
            if value.get("expectedBytes") is not None
            else None
        ),
        checksum_algorithm=(
            str(value["checksumAlgorithm"])
            if value.get("checksumAlgorithm")
            else None
        ),
        checksum_value=str(value["checksumValue"]) if value.get("checksumValue") else None,
        license_id=str(value.get("licenseId", "")),
        license_url=str(value.get("licenseUrl", "")),
        attribution=str(value.get("attribution", "")),
        provenance_url=str(value.get("provenanceUrl", "")),
        requires_authentication=bool(value.get("requiresAuthentication", False)),
        class_translation={
            int(source_value): str(category_key)
            for source_value, category_key in translation.items()
        },
        nodata_values=tuple(int(item) for item in value.get("nodataValues", [])),
        qualifier_key=str(value["qualifierKey"]) if value.get("qualifierKey") else None,
    )
