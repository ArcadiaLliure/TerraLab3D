"""Reusable acquisition clients for refinement provider adapters."""

from .http import (
    AsyncHttpRangeClient,
    HttpAssetMetadata,
    HttpClientConfiguration,
    HttpTransportError,
)
from .ogc import (
    OgcApiCoverageRequest,
    WcsGetCoverageRequest,
    WfsGetFeatureRequest,
)
from .stac import StacApiClient, StacAsset, StacItem, StacSearchRequest

__all__ = [
    "AsyncHttpRangeClient",
    "HttpAssetMetadata",
    "HttpClientConfiguration",
    "HttpTransportError",
    "OgcApiCoverageRequest",
    "StacApiClient",
    "StacAsset",
    "StacItem",
    "StacSearchRequest",
    "WcsGetCoverageRequest",
    "WfsGetFeatureRequest",
]
