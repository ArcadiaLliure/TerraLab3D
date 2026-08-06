"""Contractes de precisió, convergència i propagació d’incertesa."""
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True, slots=True)
class NumericalResult:
    value: float
    estimated_error: float | None
    converged: bool

class RootSolver(Protocol):
    """Resol arrels sense fixar una biblioteca numèrica concreta."""
    def solve(self, function_id: str, lower: float, upper: float) -> NumericalResult: ...
