"""Serveis de domini per al progrés i els errors visibles."""
from typing import Protocol
from .models import OperationStatus, UserFacingIssue

class FeedbackStateModel(Protocol):
    """Normalitza operacions i incidències per a la presentació."""
    def reduce(self, operations: tuple[OperationStatus, ...], issues: tuple[UserFacingIssue, ...]) -> tuple[OperationStatus, ...]: ...
