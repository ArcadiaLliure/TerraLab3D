"""Provider-neutral STAC 1.x item discovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urljoin

from terralab3d.domain.refinement.errors import RefinementValidationError

from .http import AsyncHttpRangeClient, HttpTransportError


@dataclass(frozen=True, slots=True)
class StacSearchRequest:
    endpoint_url: str
    collections: tuple[str, ...]
    intersects: Mapping[str, object]
    datetime_interval: str | None = None
    page_size: int = 100
    maximum_items: int = 1000

    def __post_init__(self) -> None:
        if (
            not self.endpoint_url.strip()
            or not self.collections
            or self.page_size <= 0
            or self.maximum_items <= 0
        ):
            raise RefinementValidationError("Invalid STAC search request")


@dataclass(frozen=True, slots=True)
class StacAsset:
    key: str
    href: str
    media_type: str | None
    roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StacItem:
    item_id: str
    collection: str
    geometry: Mapping[str, object]
    bbox: tuple[float, ...]
    properties: Mapping[str, object]
    assets: tuple[StacAsset, ...]


class StacApiClient:
    def __init__(self, transport: AsyncHttpRangeClient | None = None) -> None:
        self._transport = transport or AsyncHttpRangeClient()

    async def search(self, request: StacSearchRequest) -> tuple[StacItem, ...]:
        search_url = f"{request.endpoint_url.rstrip('/')}/search"
        body: dict[str, object] = {
            "collections": list(request.collections),
            "intersects": dict(request.intersects),
            "limit": request.page_size,
        }
        if request.datetime_interval:
            body["datetime"] = request.datetime_interval
        payload = await self._transport.request_json("POST", search_url, json_body=body)
        items: list[StacItem] = []
        while True:
            features = payload.get("features")
            if not isinstance(features, list):
                raise HttpTransportError("STAC response has no feature array")
            for feature in features:
                if isinstance(feature, dict):
                    items.append(_parse_item(feature))
                    if len(items) >= request.maximum_items:
                        return tuple(items)
            next_url = _next_link(payload, request.endpoint_url)
            if next_url is None:
                return tuple(items)
            payload = await self._transport.request_json("GET", next_url)


def _parse_item(value: Mapping[str, Any]) -> StacItem:
    item_id = str(value.get("id", "")).strip()
    collection = str(value.get("collection", "")).strip()
    geometry = value.get("geometry")
    bbox = value.get("bbox")
    properties = value.get("properties")
    raw_assets = value.get("assets")
    if (
        not item_id
        or not collection
        or not isinstance(geometry, dict)
        or not isinstance(bbox, list)
        or not isinstance(properties, dict)
        or not isinstance(raw_assets, dict)
    ):
        raise HttpTransportError("STAC item metadata is incomplete")
    assets = tuple(
        StacAsset(
            key=str(key),
            href=str(asset.get("href", "")),
            media_type=str(asset["type"]) if asset.get("type") else None,
            roles=tuple(str(role) for role in asset.get("roles", []) if isinstance(role, str)),
        )
        for key, asset in sorted(raw_assets.items())
        if isinstance(asset, dict) and str(asset.get("href", "")).strip()
    )
    return StacItem(
        item_id=item_id,
        collection=collection,
        geometry=geometry,
        bbox=tuple(float(coordinate) for coordinate in bbox),
        properties=properties,
        assets=assets,
    )


def _next_link(payload: Mapping[str, Any], base_url: str) -> str | None:
    links = payload.get("links")
    if not isinstance(links, list):
        return None
    for link in links:
        if isinstance(link, dict) and link.get("rel") == "next" and link.get("href"):
            return urljoin(base_url, str(link["href"]))
    return None
