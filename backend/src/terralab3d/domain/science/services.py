"""Serveis de domini per als fonaments científics compartits."""
from typing import Protocol
from .models import ScientificComputationContext

class ScientificValidationModel(Protocol):
    """Valida unitats, dominis i toleràncies abans d’executar càlculs."""
    def validate_context(self, context: ScientificComputationContext) -> bool: ...
