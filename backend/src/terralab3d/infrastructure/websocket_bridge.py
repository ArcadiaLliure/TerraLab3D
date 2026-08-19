"""Pont WebSocket entre el backend en Python i el frontend Three.js.

Responsabilitats:
  - Gestionar el cicle de vida de la connexió WebSocket per a un únic client connectat.
  - Realitzar el dóna-m'hi-l'anotació tipat (``frontend_ready`` → ``handshake_ack``).
  - Rebre esdeveniments ``camera_changed`` i ``viewport_resized`` del frontend.
  - Enviar ordres ``set_camera_pose``, ``focus_direction`` i ``shutdown_requested``
    cap al frontend.
  - Coordinar un tancament net (``shutdown_requested`` → ``shutdown_complete``).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Callable, Awaitable

import aiohttp.web

log = logging.getLogger("terralab3d.bridge")

PROTOCOL_VERSION = 2

# Àlies de tipus per als manegadors de missatges del pont
MessageHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


class WebSocketBridge:
    """Meitat del servidor del pont Python ↔ Three.js."""

    def __init__(self) -> None:
        self._clients: set[Any] = set()
        self._fallback_ws: Any = None
        self._session_id: str = ""
        self._handlers: dict[str, list[MessageHandler]] = {}
        self._shutdown_event = asyncio.Event()
        self._binary_bytes_sent = 0
        self._solar_system_bridge_bytes = 0
        self._lighting_bridge_bytes = 0
        self._eclipse_snapshot_bytes = 0
        self._trajectory_bridge_bytes = 0

    @property
    def _ws(self) -> Any:
        if self._clients:
            return next(iter(self._clients))
        return self._fallback_ws

    @_ws.setter
    def _ws(self, ws: Any) -> None:
        self._fallback_ws = ws
        if ws is not None:
            self._clients.add(ws)
        else:
            self._clients.clear()

    @property
    def connected(self) -> bool:
        return len(self._clients) > 0 or self._fallback_ws is not None

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def shutdown_event(self) -> asyncio.Event:
        """S'activa quan el frontend envia ``shutdown_complete``."""
        return self._shutdown_event

    @property
    def binary_bytes_sent(self) -> int:
        return self._binary_bytes_sent

    @property
    def solar_system_bridge_bytes(self) -> int:
        return self._solar_system_bridge_bytes

    @property
    def lighting_bridge_bytes(self) -> int:
        return self._lighting_bridge_bytes

    @property
    def eclipse_snapshot_bytes(self) -> int:
        return self._eclipse_snapshot_bytes

    @property
    def trajectory_bridge_bytes(self) -> int:
        return self._trajectory_bridge_bytes

    def on(self, msg_type: str, handler: MessageHandler) -> None:
        """Registra un manegador per a un tipus de missatge específic."""
        self._handlers.setdefault(msg_type, []).append(handler)

    async def handle_websocket(
        self, request: aiohttp.web.Request,
    ) -> aiohttp.web.WebSocketResponse:
        """Gestiona una connexió WebSocket."""
        ws = aiohttp.web.WebSocketResponse(heartbeat=10)
        await ws.prepare(request)
        log.debug("WebSocket connectat")

        # Llegim el primer missatge (ha de ser frontend_ready) per validar la versió
        msg = await ws.receive()
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
                if data.get("type") == "frontend_ready":
                    if data.get("protocolVersion", 1) < 2:
                        log.warning("Connexió rebutjada: protocol_version antiga (pestanya zombie)")
                        await ws.close(code=4001, message=b"Old protocol version")
                        return ws
            except json.JSONDecodeError:
                pass

        self._clients.add(ws)
        self._session_id = uuid.uuid4().hex[:16]

        # Despatxa el primer missatge llegit
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
                await self._dispatch(data)
            except Exception:
                pass

        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except json.JSONDecodeError:
                        log.warning("JSON no vàlid des del frontend: %s", msg.data[:200])
                        continue
                    await self._dispatch(data)
                elif msg.type in (
                    aiohttp.WSMsgType.ERROR,
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.CLOSING,
                ):
                    break
        except Exception:
            log.exception("Error a WebSocket")
        finally:
            self._clients.discard(ws)
            log.debug("WebSocket desconnectat (clients actius: %d)", len(self._clients))

        return ws

    async def send(self, msg: dict[str, Any]) -> None:
        """Envia un missatge JSON a tots els frontends connectats."""
        for ws in list(self._clients):
            if not ws.closed:
                try:
                    await ws.send_json(msg)
                except Exception:
                    self._clients.discard(ws)

    async def send_binary_resource(
        self,
        resource_id: str,
        version: str,
        metadata: dict[str, Any],
        buffer: bytes,
    ) -> None:
        """Envia un recurs binari als frontends connectats."""
        is_land_cover = metadata.get("role") == "land_cover_tile"
        if is_land_cover:
            log.info("MGP: WebSocketBridge.send_binary_resource [INICI]")
        if not self._clients:
            if is_land_cover:
                log.info("MGP: WebSocketBridge.send_binary_resource [FI]")
            return

        header_bytes = json.dumps(metadata).encode("utf-8")
        header_len = len(header_bytes)

        import struct
        message = struct.pack("<I", header_len) + header_bytes + buffer
        for ws in list(self._clients):
            if not ws.closed:
                try:
                    await ws.send_bytes(message)
                except Exception:
                    self._clients.discard(ws)
        self._binary_bytes_sent += len(message)
        log.debug(
            "Recurs binari enviat: %s v%s (%d bytes header + %d bytes payload)",
            resource_id, version, header_len, len(buffer),
        )
        if is_land_cover:
            log.info("MGP: WebSocketBridge.send_binary_resource [FI]")

    async def send_star_catalog_status(self, status: dict[str, Any]) -> None:
        """Envia l'estat del catàleg estel·lar a la UI."""
        await self.send(status)

    async def send_celestial_frame_transform(self, transform: dict[str, Any]) -> None:
        """Envia la transformació equatorial→ENU al frontend.

        Només quan canvia LST/latitud. NO per frame visual.
        """
        await self.send(transform)

    async def send_star_pick_resolved(
        self,
        request_id: str,
        generation: int,
        status: str,
        star_data: dict[str, Any] | None = None,
    ) -> None:
        """Envia la resolució d'un pick estel·lar al frontend (Pas 6).

        source_id es serialitza com string decimal per preservar int64.
        """
        payload: dict[str, Any] = {
            "type": "star_pick_resolved",
            "requestId": request_id,
            "generation": generation,
            "status": status,
        }
        if star_data is not None:
            payload["star"] = star_data
        await self.send(payload)

    # ─── Astronomical Search (Pas 12) ──────────────────────────────────

    async def send_astronomical_search_result(
        self,
        request_id: str,
        generation: int,
        status: str,
        results: list[dict[str, Any]]
    ) -> None:
        await self.send({
            "type": "astronomical_search_result",
            "requestId": request_id,
            "generation": generation,
            "status": status,
            "results": results,
        })


    async def send_set_camera_pose(
        self,
        az: float, alt: float, fov: float, roll: float = 0.0,
        transition_ms: float | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "type": "set_camera_pose",
            "azimuthDeg": az,
            "altitudeDeg": alt,
            "horizontalFovDeg": fov,
            "rollDeg": roll,
        }
        if transition_ms is not None:
            payload["transitionMs"] = transition_ms
        await self.send(payload)

    async def send_focus_direction(
        self,
        az: float, alt: float,
        transition_ms: float | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "type": "focus_direction",
            "azimuthDeg": az,
            "altitudeDeg": alt,
        }
        if transition_ms is not None:
            payload["transitionMs"] = transition_ms
        await self.send(payload)

    async def send_observer_location_changed(
        self,
        lat: float,
        lon: float,
        elevation: float | None,
        effective_height: float | None,
        source: str,
        height_offset: float = 0.0,
        navigation: bool = False,
    ) -> None:
        await self.send({
            "type": "observer_location_changed",
            "lat": lat,
            "lon": lon,
            "elevation": elevation,
            "effectiveHeight": effective_height,
            "elevationSource": source,
            "heightOffset": height_offset,
            "navigation": navigation,
        })

    async def send_navigation_coordinates_changed(
        self,
        latitude_deg: float,
        longitude_deg: float,
    ) -> None:
        """Publish GPS coordinates without waiting for a DEM height lookup."""

        await self.send({
            "type": "navigation_coordinates_changed",
            "lat": latitude_deg,
            "lon": longitude_deg,
        })

    async def send_horizon_status(self, status: dict[str, Any]) -> None:
        await self.send(status)

    async def send_simulation_time_snapshot(
        self,
        current_time_iso: str,
        julian_day: float,
        lst_deg: float,
        sun_altitudes: list[float],
        is_realtime: bool,
    ) -> None:
        await self.send({
            "type": "simulation_time_snapshot",
            "currentTimeIso": current_time_iso,
            "julianDay": julian_day,
            "lstDeg": lst_deg,
            "sunAltitudes": sun_altitudes,
            "isRealtime": is_realtime,
        })

    async def send_sky_environment_snapshot(self, snapshot: Any) -> None:
        """Envia l'estat complet del cel i atmosfera (Pas 7)."""
        payload = snapshot.to_dict()
        payload["type"] = "sky_environment_snapshot"
        await self.send(payload)

    async def send_solar_system_snapshot(self, snapshot: Any) -> int:
        """Send the compact Step 8 DTO and return its UTF-8 JSON size."""
        payload = snapshot.to_dict()
        payload["type"] = "solar_system_snapshot"
        byte_count = len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        self._solar_system_bridge_bytes = byte_count
        await self.send(payload)
        return byte_count

    async def send_lighting_environment_snapshot(self, snapshot: Any) -> int:
        """Send the compact Step 8.7 DTO; it never contains GPU assets."""

        payload = snapshot.to_dict()
        payload["type"] = "lighting_environment_snapshot"
        byte_count = len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        self._lighting_bridge_bytes = byte_count
        await self.send(payload)
        return byte_count

    async def send_astronomical_event_snapshot(self, snapshot: Any) -> int:
        payload = snapshot.to_dict()
        payload["type"] = "astronomical_event_snapshot"
        byte_count = len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        self._eclipse_snapshot_bytes = byte_count
        await self.send(payload)
        return byte_count

    async def send_event_search_result(self, result: Any) -> int:
        payload = result.to_dict()
        payload["type"] = "event_search_result"
        byte_count = len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        await self.send(payload)
        return byte_count

    async def send_angular_separation_result(self, result: Any) -> int:
        payload = result.to_dict()
        payload["type"] = "angular_separation_result"
        byte_count = len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        await self.send(payload)
        return byte_count

    async def send_moon_surface_resource(self, descriptor: Any) -> None:
        """Send only the small local resource descriptor, never texture bytes."""

        payload = descriptor.to_dict()
        payload["type"] = "moon_surface_resource"
        await self.send(payload)

    async def send_planet_texture_manifest(self, descriptor: Any) -> None:
        payload = descriptor.texture_manifest_dict()
        payload["type"] = "planet_texture_manifest"
        await self.send(payload)

    async def send_satellite_catalog_manifest(self, descriptor: Any) -> None:
        payload = descriptor.catalog_manifest_dict()
        payload["type"] = "solar_system_catalog_manifest"
        await self.send(payload)

    async def send_orbit_geometry(self, resource: Any) -> int:
        await self.send_binary_resource(
            resource.resource_id,
            resource.version,
            resource.metadata,
            resource.payload,
        )
        return len(resource.payload)

    async def send_apparent_trajectory(self, resource: Any) -> int:
        await self.send_binary_resource(
            resource.resource_id,
            resource.version,
            resource.metadata,
            resource.payload,
        )
        self._trajectory_bridge_bytes = len(resource.payload)
        return len(resource.payload)

    async def send_resource_catalog_snapshot(self, snapshot: Any) -> None:
        payload = snapshot
        if hasattr(snapshot, "to_dict"):
            payload = snapshot.to_dict()
        payload["type"] = "resource_catalog_snapshot"
        await self.send(payload)

    async def send_download_job_snapshot(self, snapshot: Any) -> None:
        payload = snapshot
        if hasattr(snapshot, "to_dict"):
            payload = snapshot.to_dict()
        payload["type"] = "download_job_snapshot"
        await self.send(payload)

    async def send_location_error(self, message: str) -> None:
        await self.send({
            "type": "location_error",
            "message": message,
        })

    async def request_shutdown(self) -> None:
        """Demana al frontend que netegi recursos i confirmi amb shutdown_complete."""
        await self.send({"type": "shutdown_requested"})

    # ─── Privat ──────────────────────────────────────────────────────

    async def _dispatch(self, data: dict[str, Any]) -> None:
        msg_type = data.get("type")
        if not isinstance(msg_type, str):
            log.warning("Missatge sense tipus: %s", data)
            return

        if msg_type not in ("camera_changed", "set_simulation_time", "camera_pose_changed"):
            log.debug("S'ha rebut missatge de tipus: %s", msg_type)
        else:
            log.debug("S'ha rebut missatge de tipus: %s", msg_type)

        if msg_type == "frontend_ready":
            await self._handle_handshake(data)
        elif msg_type == "shutdown_complete":
            log.debug("El frontend ha confirmat el tancament")
            self._shutdown_event.set()
        
        handlers = self._handlers.get(msg_type, [])
        for handler in handlers:
            try:
                result = handler(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                log.exception("Error executant handler pel missatge %s", msg_type)

    async def _handle_handshake(self, _data: dict[str, Any]) -> None:
        self._connected = True
        log.debug("Handshake completat — sessió %s", self._session_id)
        await self.send({
            "type": "handshake_ack",
            "sessionId": self._session_id,
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": ["camera", "viewport", "shutdown"],
        })
