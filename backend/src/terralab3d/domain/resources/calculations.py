"""Contractes de càlcul científic pur per a recursos binaris i cicle de vida."""

from typing import Protocol


class ResourceBudgetCalculator(Protocol):
    """Defineix els càlculs purs de recursos binaris i cicle de vida sense I/O ni renderitzat."""
    def fits_budget(self, resident_bytes: int, requested_bytes: int, budget_bytes: int) -> bool: ...
