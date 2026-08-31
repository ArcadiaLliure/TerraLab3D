"""Bounded asynchronous HTTP and byte-range access for provider adapters."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

import aiohttp

from terralab3d.domain.refinement.errors import RefinementError, RefinementValidationError


class HttpTransportError(RefinementError):
    """A provider HTTP contract failed after bounded retries."""


@dataclass(frozen=True, slots=True)
class HttpClientConfiguration:
    timeout_seconds: float = 30.0
    retry_count: int = 2
    retry_backoff_seconds: float = 0.25
    maximum_concurrency: int = 8
    user_agent: str = "TerraLab3D/0.1 refinement-client"

    def __post_init__(self) -> None:
        if (
            self.timeout_seconds <= 0
            or self.retry_count < 0
            or self.retry_backoff_seconds < 0
            or self.maximum_concurrency <= 0
            or not self.user_agent.strip()
        ):
            raise RefinementValidationError("Invalid HTTP acquisition configuration")


@dataclass(frozen=True, slots=True)
class HttpAssetMetadata:
    url: str
    size_bytes: int | None
    accepts_ranges: bool
    etag: str | None
    content_type: str | None


class AsyncHttpRangeClient:
    """Share timeout, retry and concurrency rules across remote providers."""

    _TRANSIENT_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})

    def __init__(self, configuration: HttpClientConfiguration | None = None) -> None:
        self._configuration = configuration or HttpClientConfiguration()

    async def request_json(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        json_body: Mapping[str, object] | None = None,
    ) -> dict[str, Any]:
        self._validate_url(url)
        timeout = aiohttp.ClientTimeout(total=self._configuration.timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout, headers=self._headers()) as session:
            response = await self._request(
                session,
                method,
                url,
                params=params,
                json_body=json_body,
            )
            async with response:
                try:
                    payload = await response.json(content_type=None)
                except (aiohttp.ContentTypeError, ValueError) as exc:
                    raise HttpTransportError(f"HTTP response from {url} is not JSON") from exc
        if not isinstance(payload, dict):
            raise HttpTransportError(f"HTTP response from {url} is not a JSON object")
        return payload

    async def probe(self, url: str) -> HttpAssetMetadata | None:
        """Read object metadata without downloading it; missing tiles return None."""

        self._validate_url(url)
        timeout = aiohttp.ClientTimeout(total=self._configuration.timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout, headers=self._headers()) as session:
            response = await self._request(
                session,
                "HEAD",
                url,
                allowed_missing=True,
                allowed_statuses={200, 405},
            )
            async with response:
                if response.status in {404, 410}:
                    return None
                if response.status == 405:
                    return await self._probe_with_range(session, url)
                return self._metadata(url, response.headers)

    async def probe_many(
        self,
        urls: Sequence[str],
    ) -> tuple[HttpAssetMetadata | None, ...]:
        semaphore = asyncio.Semaphore(self._configuration.maximum_concurrency)

        async def bounded(url: str) -> HttpAssetMetadata | None:
            async with semaphore:
                return await self.probe(url)

        return tuple(await asyncio.gather(*(bounded(url) for url in urls)))

    async def read_range(self, url: str, start: int, end: int) -> bytes:
        if start < 0 or end < start:
            raise RefinementValidationError("HTTP byte range is invalid")
        self._validate_url(url)
        timeout = aiohttp.ClientTimeout(total=self._configuration.timeout_seconds)
        headers = {**self._headers(), "Range": f"bytes={start}-{end}"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            response = await self._request(
                session,
                "GET",
                url,
                allowed_statuses={200, 206},
            )
            async with response:
                payload = await response.read()
        expected = end - start + 1
        if response.status == 206 and len(payload) != expected:
            raise HttpTransportError(
                f"HTTP range response from {url} returned {len(payload)} bytes, expected {expected}"
            )
        if response.status == 200 and start > 0:
            raise HttpTransportError(f"HTTP server for {url} ignored a non-zero byte range")
        return payload[:expected]

    async def _probe_with_range(
        self,
        session: aiohttp.ClientSession,
        url: str,
    ) -> HttpAssetMetadata | None:
        response = await self._request(
            session,
            "GET",
            url,
            headers={"Range": "bytes=0-0"},
            allowed_missing=True,
            allowed_statuses={200, 206},
        )
        async with response:
            if response.status in {404, 410}:
                return None
            await response.read()
            return self._metadata(url, response.headers)

    async def _request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        json_body: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        allowed_missing: bool = False,
        allowed_statuses: set[int] | None = None,
    ) -> aiohttp.ClientResponse:
        last_error: Exception | None = None
        statuses = allowed_statuses or {200}
        if allowed_missing:
            statuses = {*statuses, 404, 410}
        for attempt in range(self._configuration.retry_count + 1):
            try:
                response = await session.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    headers=headers,
                )
                if response.status in statuses:
                    return response
                body = await response.text()
                response.release()
                error = HttpTransportError(
                    f"HTTP {response.status} from {url}: {body[:200]}"
                )
                if response.status not in self._TRANSIENT_STATUS:
                    raise error
                last_error = error
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_error = exc
            if attempt < self._configuration.retry_count:
                await asyncio.sleep(
                    self._configuration.retry_backoff_seconds * (2**attempt)
                )
        raise HttpTransportError(f"HTTP request to {url} failed after retries") from last_error

    @staticmethod
    def _metadata(url: str, headers: aiohttp.typedefs.LooseHeaders) -> HttpAssetMetadata:
        normalized = {str(key).lower(): str(value) for key, value in headers.items()}
        raw_size = normalized.get("content-length")
        size = int(raw_size) if raw_size and raw_size.isdigit() else None
        content_range = normalized.get("content-range")
        if content_range and "/" in content_range:
            total = content_range.rsplit("/", 1)[1]
            if total.isdigit():
                size = int(total)
        return HttpAssetMetadata(
            url=url,
            size_bytes=size,
            accepts_ranges=(
                normalized.get("accept-ranges", "").lower() == "bytes"
                or content_range is not None
            ),
            etag=normalized.get("etag", "").strip('"') or None,
            content_type=normalized.get("content-type"),
        )

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self._configuration.user_agent}

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RefinementValidationError("Provider asset URL must use HTTP or HTTPS")
