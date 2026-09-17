"""Cas d'ús autoritatiu del catàleg i el document de constel·lacions."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Awaitable, Callable

from terralab3d.application.ports.persistence import PreferencesPort
from terralab3d.application.star_pick_resolver import StarPickResolver
from terralab3d.domain.constellations.calculations import (
    ConstellationValidationError,
    SphericalConstellationCalculator,
)
from terralab3d.domain.constellations.models import (
    ConstellationDocument,
    ConstellationNode,
    EditableConstellation,
)
from terralab3d.domain.constellations.services import ConstellationDocumentHistory
from terralab3d.domain.geometry import EquatorialCoordinate
from terralab3d.domain.identifiers import ConstellationId
from terralab3d.domain.stars.star_pick_models import StarPickRequest
from terralab3d.infrastructure.catalogs.constellations import PackagedConstellationCatalog


log = logging.getLogger("terralab3d.constellations")
Publisher = Callable[[dict[str, Any]], Awaitable[None]]
PREFERENCES_KEY = "constellations.v1"
LEGACY_KEY = "terralab_constellations"


class ConstellationCoordinator:
    def __init__(
        self,
        preferences: PreferencesPort,
        publish: Publisher,
        star_pick_resolver: StarPickResolver,
        catalog: PackagedConstellationCatalog | None = None,
        history_limit: int = 256,
    ) -> None:
        self.catalog = catalog or PackagedConstellationCatalog()
        self._preferences = preferences
        self._publish = publish
        self._star_pick_resolver = star_pick_resolver
        self._calculator = SphericalConstellationCalculator()
        document, warning = self._load_document()
        self._history = ConstellationDocumentHistory(document, history_limit)
        self._warning = warning
        self._selected_id: ConstellationId | None = None
        self._editing = False
        self._start_new_stroke = False
        self._entity_versions = {str(item.constellation_id): 1 for item in document.constellations}

    @property
    def revision(self) -> int:
        return self._history.document.revision

    async def publish_current(self, *, include_catalog: bool = False) -> None:
        if include_catalog:
            await self._publish(self.catalog.snapshot_payload())
        await self._publish(self.snapshot_payload())

    async def apply(self, data: dict[str, Any]) -> None:
        requested = int(data.get("documentRevision", -1))
        if requested != self.revision + 1:
            raise ConstellationValidationError(
                "documentRevision",
                f"revisió obsoleta: esperada {self.revision + 1}, rebuda {requested}",
            )
        action = str(data.get("action", ""))
        before = self._history.document
        if action == "create_group":
            raw_name = str(data.get("name", "Nova constel·lació")).strip()
            name = raw_name[:80] or "Nova constel·lació"
            raw_id = str(data.get("constellationId", "")).strip()
            constellation_id = ConstellationId(raw_id or f"constellation:user:{uuid.uuid4()}")
            if any(item.constellation_id == constellation_id for item in self._history.document.constellations):
                raise ConstellationValidationError("constellationId", "la constel·lació ja existeix")
            self._history.create(EditableConstellation(constellation_id, name))
            self._selected_id = constellation_id
            self._editing = True
            self._start_new_stroke = False
        elif action == "append_node":
            constellation_id = self._required_id(data)
            response = self._star_pick_resolver.resolve(StarPickRequest(
                request_id=str(data.get("requestId", uuid.uuid4())),
                generation=requested,
                resource_id=str(data["resourceId"]),
                resource_version=str(data["resourceVersion"]),
                catalog_index=int(data["catalogIndex"]),
                purpose="constellation_snap",
            ))
            if response.status != "ok" or response.resolved is None:
                raise ConstellationValidationError("starRef", f"referència estel·lar {response.status}")
            star = response.resolved
            coordinate = self._calculator.validate_coordinate(EquatorialCoordinate(star.ra_deg, star.dec_deg))
            self._history.append_node(constellation_id, ConstellationNode(
                node_id=f"node:{uuid.uuid4()}",
                coordinate=coordinate,
                source_id=str(star.source_id),
                resource_id=star.resource_id,
                resource_version=star.version,
                catalog_index=star.catalog_index,
                starts_new_stroke=self._start_new_stroke,
            ))
            self._selected_id = constellation_id
            self._start_new_stroke = False
        elif action == "finish_group":
            self._editing = False
            self._start_new_stroke = False
        elif action == "resume_from_node":
            constellation_id = self._required_id(data)
            node_id = str(data.get("nodeId", ""))
            group = self._history.require(constellation_id)
            source = next((node for node in group.nodes if node.node_id == node_id), None)
            if source is None:
                raise ConstellationValidationError("nodeId", "el node no existeix")
            self._history.append_node(constellation_id, ConstellationNode(
                node_id=f"node:{uuid.uuid4()}",
                coordinate=source.coordinate,
                source_id=source.source_id,
                star_name=source.star_name,
                resource_id=source.resource_id,
                resource_version=source.resource_version,
                catalog_index=source.catalog_index,
                starts_new_stroke=True,
            ))
            self._selected_id = constellation_id
            self._editing = True
        elif action == "new_stroke":
            self._history.require(self._required_id(data))
            self._start_new_stroke = True
        elif action == "select":
            value = data.get("constellationId")
            selected = None if value in (None, "") else ConstellationId(str(value))
            if selected is not None:
                self._history.require(selected)
            self._selected_id = selected
        elif action == "set_editing":
            enabled = data.get("editing")
            if not isinstance(enabled, bool):
                raise ConstellationValidationError("editing", "el mode d'edició ha de ser booleà")
            self._editing = enabled
            if not enabled:
                self._start_new_stroke = False
        elif action == "rename_group":
            name = str(data.get("name", "")).strip()
            if not name:
                raise ConstellationValidationError("name", "el nom no pot ser buit")
            self._history.rename(self._required_id(data), name[:80])
        elif action == "delete_selection":
            constellation_id = self._required_id(data)
            self._history.delete(constellation_id)
            if self._selected_id == constellation_id:
                self._selected_id = None
        elif action == "undo":
            self._history.undo()
        elif action == "redo":
            self._history.redo()
        elif action == "clear":
            self._history.clear()
            self._selected_id = None
        else:
            raise ConstellationValidationError("action", "operació de constel·lació desconeguda")

        if self._history.document != before:
            self._refresh_entity_versions(before)
            active_ids = {item.constellation_id for item in self._history.document.constellations}
            if self._selected_id is not None and self._selected_id not in active_ids:
                self._selected_id = None
                self._editing = False
                self._start_new_stroke = False
            self._save_document()
        await self._publish(self.snapshot_payload())

    def snapshot_payload(self) -> dict[str, Any]:
        document = self._history.document
        return {
            "type": "constellation_document",
            "schemaVersion": 1,
            "documentRevision": document.revision,
            "constellations": [self._group_payload(group) for group in document.constellations],
            "selectedConstellationId": None if self._selected_id is None else str(self._selected_id),
            "editing": self._editing,
            "canUndo": self._history.can_undo,
            "canRedo": self._history.can_redo,
            "warning": self._warning,
        }

    def _group_payload(self, group: EditableConstellation) -> dict[str, Any]:
        strokes: list[list[dict[str, Any]]] = []
        current: list[dict[str, Any]] = []
        nodes = []
        for node in group.nodes:
            payload = {
                "nodeId": node.node_id,
                "raDeg": node.coordinate.right_ascension_deg,
                "decDeg": node.coordinate.declination_deg,
                "sourceId": node.source_id,
                "starName": node.star_name,
                "startsNewStroke": node.starts_new_stroke,
            }
            nodes.append(payload)
            if node.starts_new_stroke and current:
                strokes.append(current)
                current = []
            current.append({"raDeg": payload["raDeg"], "decDeg": payload["decDeg"]})
        if current:
            strokes.append(current)
        return {
            "constellationId": str(group.constellation_id),
            "name": group.name,
            "entityVersion": self._entity_versions.get(str(group.constellation_id), 1),
            "nodes": nodes,
            "strokes": strokes,
        }

    def _required_id(self, data: dict[str, Any]) -> ConstellationId:
        raw = data.get("constellationId", self._selected_id)
        if raw in (None, ""):
            raise ConstellationValidationError("constellationId", "cal seleccionar una constel·lació")
        value = ConstellationId(str(raw))
        self._history.require(value)
        return value

    def _load_document(self) -> tuple[ConstellationDocument, str | None]:
        raw = self._preferences.load_text(PREFERENCES_KEY)
        source_key = PREFERENCES_KEY
        migrated = False
        if raw is None:
            raw = self._preferences.load_text(LEGACY_KEY)
            source_key = LEGACY_KEY
            migrated = raw is not None
        if raw is None:
            return ConstellationDocument(), None
        try:
            document = self._document_from_json(json.loads(raw))
            if migrated:
                self._save_raw_document(document)
            return document, "S'ha importat el document antic sense modificar l'original." if migrated else None
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, ConstellationValidationError) as exc:
            backup = getattr(self._preferences, "backup_invalid", lambda _key: None)(source_key)
            log.warning("MGP: [ConstellationCoordinator] [load] [%s; backup=%s]", exc, backup)
            empty_document = ConstellationDocument()
            self._save_raw_document(empty_document)
            return empty_document, "El document invàlid s'ha preservat en una còpia datada; s'ha iniciat un document buit."

    def _document_from_json(self, payload: Any) -> ConstellationDocument:
        if isinstance(payload, list):
            raw_groups = payload
        elif isinstance(payload, dict):
            version = int(payload.get("schemaVersion", 0))
            if version not in {0, 1}:
                raise ValueError("versió de document no compatible")
            raw_groups = payload.get("constellations", payload.get("groups", []))
        else:
            raise ValueError("document invàlid")
        groups = []
        for group_index, raw_group in enumerate(raw_groups):
            group_id = ConstellationId(str(raw_group.get("constellationId", raw_group.get("id", f"constellation:migrated:{group_index}"))))
            name = str(raw_group.get("name", f"Constel·lació {group_index + 1}")).strip() or f"Constel·lació {group_index + 1}"
            nodes = []
            for node_index, raw_node in enumerate(raw_group.get("nodes", raw_group.get("points", []))):
                coordinate_payload = raw_node.get("coordinate", raw_node)
                coordinate = self._calculator.validate_coordinate(EquatorialCoordinate(
                    float(coordinate_payload.get("raDeg", coordinate_payload.get("ra", 0.0))),
                    float(coordinate_payload.get("decDeg", coordinate_payload.get("dec", 0.0))),
                ))
                nodes.append(ConstellationNode(
                    node_id=str(raw_node.get("nodeId", f"node:migrated:{group_index}:{node_index}")),
                    coordinate=coordinate,
                    source_id=None if raw_node.get("sourceId") is None else str(raw_node.get("sourceId")),
                    star_name=raw_node.get("starName"),
                    resource_id=raw_node.get("resourceId"),
                    resource_version=raw_node.get("resourceVersion"),
                    catalog_index=None if raw_node.get("catalogIndex") is None else int(raw_node["catalogIndex"]),
                    starts_new_stroke=bool(raw_node.get("startsNewStroke", raw_node.get("starts_new_stroke", False))),
                ))
            groups.append(EditableConstellation(group_id, name, tuple(nodes)))
        return ConstellationDocument(1, 0, tuple(groups))

    def _save_document(self) -> None:
        self._save_raw_document(self._history.document)

    def _save_raw_document(self, document: ConstellationDocument) -> None:
        payload = {
            "documentType": "terralab3d.constellations",
            "schemaVersion": 1,
            "constellations": [
                {
                    "constellationId": str(group.constellation_id),
                    "name": group.name,
                    "nodes": [
                        {
                            "nodeId": node.node_id,
                            "raDeg": node.coordinate.right_ascension_deg,
                            "decDeg": node.coordinate.declination_deg,
                            "sourceId": node.source_id,
                            "starName": node.star_name,
                            "resourceId": node.resource_id,
                            "resourceVersion": node.resource_version,
                            "catalogIndex": node.catalog_index,
                            "startsNewStroke": node.starts_new_stroke,
                        }
                        for node in group.nodes
                    ],
                }
                for group in document.constellations
            ],
        }
        self._preferences.save_text(PREFERENCES_KEY, json.dumps(payload, ensure_ascii=False, indent=2))

    def _refresh_entity_versions(self, before: ConstellationDocument) -> None:
        previous = {str(item.constellation_id): item for item in before.constellations}
        current = {str(item.constellation_id): item for item in self._history.document.constellations}
        for key, item in current.items():
            if previous.get(key) != item:
                self._entity_versions[key] = self._entity_versions.get(key, 0) + 1
        for key in set(previous) - set(current):
            self._entity_versions.pop(key, None)
