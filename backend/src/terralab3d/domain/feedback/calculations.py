"""Contractes de càlcul científic pur per a progrés, errors, mode de reserva i estat visible."""

from typing import Protocol
from terralab3d.domain.feedback.models import OperationStatus

class ProgressAggregationCalculator(Protocol):
    """Defineix els càlculs purs de progrés, errors, mode de reserva i estat visible sense I/O ni renderitzat."""
    def aggregate(self, operations: tuple[OperationStatus, ...]) -> float | None: ...
