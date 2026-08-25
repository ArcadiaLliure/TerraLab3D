"""Immutable analytical OGC request builders used by raster/vector providers."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from terralab3d.domain.refinement.errors import RefinementValidationError


@dataclass(frozen=True, slots=True)
class WcsGetCoverageRequest:
    endpoint_url: str
    coverage_id: str
    bbox: tuple[float, float, float, float]
    crs: str
    output_format: str = "image/tiff"
    version: str = "2.0.1"

    def url(self) -> str:
        _validate_request(self.endpoint_url, self.coverage_id, self.bbox, self.crs)
        params = {
            "service": "WCS",
            "version": self.version,
            "request": "GetCoverage",
            "coverageId": self.coverage_id,
            "subset": (
                f"E({self.bbox[0]},{self.bbox[2]}),"
                f"N({self.bbox[1]},{self.bbox[3]})"
            ),
            "subsettingCrs": self.crs,
            "outputCrs": self.crs,
            "format": self.output_format,
        }
        return f"{self.endpoint_url.rstrip('?')}?{urlencode(params, safe='(),:/')}"


@dataclass(frozen=True, slots=True)
class OgcApiCoverageRequest:
    endpoint_url: str
    collection_id: str
    bbox: tuple[float, float, float, float]
    crs: str
    output_format: str = "image/tiff"

    def url(self) -> str:
        _validate_request(self.endpoint_url, self.collection_id, self.bbox, self.crs)
        params = {
            "bbox": ",".join(str(value) for value in self.bbox),
            "bbox-crs": self.crs,
            "crs": self.crs,
            "f": self.output_format,
        }
        return (
            f"{self.endpoint_url.rstrip('/')}/collections/{self.collection_id}/coverage?"
            f"{urlencode(params, safe=',:/')}"
        )


@dataclass(frozen=True, slots=True)
class WfsGetFeatureRequest:
    endpoint_url: str
    type_name: str
    bbox: tuple[float, float, float, float]
    crs: str = "EPSG:4326"
    count: int = 1000
    start_index: int = 0

    def url(self) -> str:
        _validate_request(self.endpoint_url, self.type_name, self.bbox, self.crs)
        if self.count <= 0 or self.start_index < 0:
            raise RefinementValidationError("Invalid WFS pagination")
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": self.type_name,
            "bbox": f"{','.join(str(value) for value in self.bbox)},{self.crs}",
            "outputFormat": "application/json",
            "count": self.count,
            "startIndex": self.start_index,
        }
        return f"{self.endpoint_url.rstrip('?')}?{urlencode(params, safe=',:/')}"


def _validate_request(
    endpoint_url: str,
    identifier: str,
    bbox: tuple[float, float, float, float],
    crs: str,
) -> None:
    if not endpoint_url.startswith(("http://", "https://")):
        raise RefinementValidationError("OGC endpoint must use HTTP or HTTPS")
    if not identifier.strip() or not crs.strip():
        raise RefinementValidationError("OGC request metadata is incomplete")
    west, south, east, north = bbox
    if west >= east or south >= north:
        raise RefinementValidationError("OGC request bbox is empty")
