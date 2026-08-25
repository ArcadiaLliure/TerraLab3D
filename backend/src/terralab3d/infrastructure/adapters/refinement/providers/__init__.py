"""External provider adapters for TLST refinements."""

from .clms import ClmsODataAdapter, ClmsProviderConfiguration
from .corine import CorineLandCoverAdapter, CorineProviderConfiguration
from .icgc import IcgcLandCoverAdapter, IcgcLandCoverConfiguration

__all__ = [
    "ClmsODataAdapter",
    "ClmsProviderConfiguration",
    "CorineLandCoverAdapter",
    "CorineProviderConfiguration",
    "IcgcLandCoverAdapter",
    "IcgcLandCoverConfiguration",
]
