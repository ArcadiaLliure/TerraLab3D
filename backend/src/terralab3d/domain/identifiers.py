"""Identificadors forts compartits pels paquets purs de domini."""
from typing import NewType

ObserverId = NewType("ObserverId", str)
StarId = NewType("StarId", str)
CelestialBodyId = NewType("CelestialBodyId", str)
DeepSkyObjectId = NewType("DeepSkyObjectId", str)
TerrainTileId = NewType("TerrainTileId", str)
MeasurementId = NewType("MeasurementId", str)
ConstellationId = NewType("ConstellationId", str)
ResourceId = NewType("ResourceId", str)
VariantId = NewType("VariantId", str)
LayerId = NewType("LayerId", str)
DatasetId = NewType("DatasetId", str)
OperationId = NewType("OperationId", str)
EntityId = NewType("EntityId", str)
