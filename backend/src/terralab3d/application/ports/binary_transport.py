"""Port de transport binari per a recursos grans i versionats."""
from typing import Protocol
from terralab3d.domain.identifiers import ResourceId

class BinaryTransportPort(Protocol):
    """Publica recursos binaris sense JSON ni Base64."""
    def publish(self, resource_id: ResourceId, version: int, payload: memoryview) -> str: ...
    def revoke(self, resource_id: ResourceId, version: int) -> None: ...
