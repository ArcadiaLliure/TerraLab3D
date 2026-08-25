"""External provider adapters for TLST refinements."""

from .clms import ClmsODataAdapter, ClmsProviderConfiguration
from .corine import CorineLandCoverAdapter, CorineProviderConfiguration
from .icgc import IcgcLandCoverAdapter, IcgcLandCoverConfiguration
from .rollout import ProviderRollout, ProviderRolloutState, refinement_provider_rollout
from .water_wetness import WaterWetnessConfiguration, WaterWetnessImageServerAdapter
from .worldcover import (
    WorldCoverCogAdapter,
    WorldCoverConfiguration,
    worldcover_refinement_products,
)

__all__ = [
    "ClmsODataAdapter",
    "ClmsProviderConfiguration",
    "CorineLandCoverAdapter",
    "CorineProviderConfiguration",
    "IcgcLandCoverAdapter",
    "IcgcLandCoverConfiguration",
    "ProviderRollout",
    "ProviderRolloutState",
    "refinement_provider_rollout",
    "WaterWetnessConfiguration",
    "WaterWetnessImageServerAdapter",
    "WorldCoverCogAdapter",
    "WorldCoverConfiguration",
    "worldcover_refinement_products",
]
