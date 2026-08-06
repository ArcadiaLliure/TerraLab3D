"""Contractes de servei purs per a la capacitat cerca."""


from typing import Protocol, Sequence
from .models import SearchQuery, SearchResult

class AstronomicalSearchModel(Protocol):
    """Ordena objectius astronòmics ja indexats."""
    def search(self, query: SearchQuery) -> Sequence[SearchResult]: ...
