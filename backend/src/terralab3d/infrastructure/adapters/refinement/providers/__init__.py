"""External provider adapters for TLST refinements."""

from .clms import ClmsODataAdapter, ClmsProviderConfiguration
from .icgc import IcgcLandCoverAdapter, IcgcLandCoverConfiguration

__all__ = [
    "ClmsODataAdapter",
    "ClmsProviderConfiguration",
    "IcgcLandCoverAdapter",
    "IcgcLandCoverConfiguration",
]
