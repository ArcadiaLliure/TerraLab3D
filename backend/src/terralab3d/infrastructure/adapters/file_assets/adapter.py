"""Especificació abstracta de l’adaptador file_assets."""
from abc import ABC, abstractmethod

class FileAssetsAdapterSpec(ABC):
    """Ubicació i límit de cicle de vida de la futura implementació concreta."""

    @abstractmethod
    def open(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError
