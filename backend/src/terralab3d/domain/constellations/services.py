"""Transicions immutables i historial de sessió dels documents d'usuari."""

from __future__ import annotations

from dataclasses import replace

from terralab3d.domain.constellations.models import (
    ConstellationDocument,
    ConstellationNode,
    EditableConstellation,
)
from terralab3d.domain.identifiers import ConstellationId


class ConstellationDocumentHistory:
    def __init__(self, document: ConstellationDocument | None = None, history_limit: int = 256) -> None:
        if history_limit < 1:
            raise ValueError("history_limit ha de ser positiu")
        self._document = document or ConstellationDocument()
        self._limit = history_limit
        self._undo: list[tuple[EditableConstellation, ...]] = []
        self._redo: list[tuple[EditableConstellation, ...]] = []

    @property
    def document(self) -> ConstellationDocument:
        return self._document

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def undo_depth(self) -> int:
        return len(self._undo)

    def create(self, value: EditableConstellation) -> ConstellationDocument:
        if any(item.constellation_id == value.constellation_id for item in self._document.constellations):
            return self._document
        return self._commit((*self._document.constellations, value))

    def replace(self, value: EditableConstellation) -> ConstellationDocument:
        items = list(self._document.constellations)
        index = next((i for i, item in enumerate(items) if item.constellation_id == value.constellation_id), None)
        if index is None or items[index] == value:
            return self._document
        items[index] = value
        return self._commit(tuple(items))

    def append_node(self, constellation_id: ConstellationId, node: ConstellationNode) -> ConstellationDocument:
        current = self.require(constellation_id)
        return self.replace(replace(current, nodes=(*current.nodes, node)))

    def rename(self, constellation_id: ConstellationId, name: str) -> ConstellationDocument:
        return self.replace(replace(self.require(constellation_id), name=name))

    def delete(self, constellation_id: ConstellationId) -> ConstellationDocument:
        items = tuple(item for item in self._document.constellations if item.constellation_id != constellation_id)
        return self._document if len(items) == len(self._document.constellations) else self._commit(items)

    def clear(self) -> ConstellationDocument:
        return self._document if not self._document.constellations else self._commit(())

    def undo(self) -> ConstellationDocument:
        if not self._undo:
            return self._document
        self._redo.append(self._document.constellations)
        return self._restore(self._undo.pop())

    def redo(self) -> ConstellationDocument:
        if not self._redo:
            return self._document
        self._undo.append(self._document.constellations)
        return self._restore(self._redo.pop())

    def require(self, constellation_id: ConstellationId) -> EditableConstellation:
        value = next((item for item in self._document.constellations if item.constellation_id == constellation_id), None)
        if value is None:
            raise KeyError(str(constellation_id))
        return value

    def _commit(self, values: tuple[EditableConstellation, ...]) -> ConstellationDocument:
        self._undo.append(self._document.constellations)
        if len(self._undo) > self._limit:
            del self._undo[0]
        self._redo.clear()
        return self._restore(values)

    def _restore(self, values: tuple[EditableConstellation, ...]) -> ConstellationDocument:
        self._document = ConstellationDocument(1, self._document.revision + 1, values)
        return self._document
