"""Especificació abstracta de l’adaptador configuration."""
from abc import ABC, abstractmethod

class ConfigurationAdapterSpec(ABC):
    """Ubicació i límit de cicle de vida de la futura implementació concreta."""

    @abstractmethod
    def open(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError
