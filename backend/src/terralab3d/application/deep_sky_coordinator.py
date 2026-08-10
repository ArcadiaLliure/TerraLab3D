"""Coordinador de dades de cel profund."""

import asyncio
import logging
from typing import Any, Callable, Awaitable

from terralab3d.infrastructure.adapters.ngc_catalog.adapter import NgcCatalogAdapter

log = logging.getLogger("terralab3d.deep_sky")

ResourcePublisher = Callable[
    [str, str, dict[str, Any], bytes],
    Awaitable[None],
]

class DeepSkyCoordinator:
    """Carrega l'índex binari de catàlegs de cel profund (ex. NGC) i l'envia al frontend."""
    
    def __init__(self, adapter: NgcCatalogAdapter):
        self._adapter = adapter
        self._resource_publisher: ResourcePublisher | None = None
        self._disposed = False
        
    def set_publishers(self, resource_publisher: ResourcePublisher) -> None:
        self._resource_publisher = resource_publisher
        
    async def publish_current_state(self) -> None:
        """Carrega l'índex binari a memòria i el publica via websocket."""
        if self._disposed or not self._resource_publisher:
            return
            
        # Pot trigar una mica si és la primera vegada que es llegeix de disc,
        # ho fem asíncronament a thread per no bloquejar.
        result = await asyncio.to_thread(self._adapter.load_index)
        if not result:
            log.info("MGP: [DeepSkyCoordinator] [Catàleg NGC no disponible (probablement no descarregat o processat)]")
            return
            
        metadata, data = result
        version = metadata["processedIndexSha256"]  # Utilitzem el hash com a versió immutable
        
        await self._resource_publisher(metadata["resourceId"], version, metadata, data)
        log.info(
            "MGP: [DeepSkyCoordinator] [S'ha publicat l'índex NGC: %d objectes (renderitzables: %d)]", 
            metadata["recordCount"], 
            metadata["renderableCount"]
        )
        
    async def shutdown(self) -> None:
        self._disposed = True
        log.info("MGP: [DeepSkyCoordinator] [Tancat]")
