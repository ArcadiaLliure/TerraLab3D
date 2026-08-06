"""Especificació abstracta de l’adaptador weather."""
from abc import ABC, abstractmethod

class WeatherAdapterSpec(ABC):
    """Ubicació i límit de cicle de vida de la futura implementació concreta."""

    @abstractmethod
    def open(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError
