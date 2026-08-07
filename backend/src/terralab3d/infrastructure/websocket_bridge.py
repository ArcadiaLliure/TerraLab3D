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

PROTOCOL_VERSION = 1

# Àlies de tipus per als manegadors de missatges del pont
MessageHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


class WebSocketBridge:
    """Meitat del servidor del pont Python ↔ Three.js."""

    def __init__(self) -> None:
        self._ws: aiohttp.web.WebSocketResponse | None = None
        self._session_id: str = ""
        self._connected = False
        self._handlers: dict[str, list[MessageHandler]] = {}
        self._shutdown_event = asyncio.Event()

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def shutdown_event(self) -> asyncio.Event:
        """S'activa quan el frontend envia ``shutdown_complete``."""
        return self._shutdown_event

    def on(self, msg_type: str, handler: MessageHandler) -> None:
        """Registra un manegador per a un tipus de missatge específic."""
        self._handlers.setdefault(msg_type, []).append(handler)

    async def handle_websocket(
        self, request: aiohttp.web.Request,
    ) -> aiohttp.web.WebSocketResponse:
        """Gestiona una nova connexió WebSocket (una a la vegada)."""
        ws = aiohttp.web.WebSocketResponse(heartbeat=10)
        await ws.prepare(request)
        log.info("WebSocket connectat")

        # Només un client a la vegada
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()

        self._ws = ws
        self._connected = False
        self._session_id = uuid.uuid4().hex[:16]

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
            self._connected = False
            self._ws = None
            log.info("WebSocket desconnectat")
            # Senyalitza el tancament en desconnectar (navegador tancat)
            self._shutdown_event.set()

        return ws

    async def send(self, msg: dict[str, Any]) -> None:
        """Envia un missatge JSON al frontend connectat."""
        if self._ws and not self._ws.closed:
            await self._ws.send_json(msg)

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
        lat: float, lon: float, elevation: float, effective_height: float, source: str
    ) -> None:
        await self.send({
            "type": "observer_location_changed",
            "lat": lat,
            "lon": lon,
            "elevation": elevation,
            "effectiveHeight": effective_height,
            "elevationSource": source,
        })

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

        if msg_type not in ("camera_changed", "set_simulation_time"):
            log.info("S'ha rebut missatge de tipus: %s", msg_type)
        else:
            log.debug("S'ha rebut missatge de tipus: %s", msg_type)

        if msg_type == "frontend_ready":
            await self._handle_handshake(data)
        elif msg_type == "shutdown_complete":
            log.info("El frontend ha confirmat el tancament")
            self._shutdown_event.set()
        
        handlers = self._handlers.get(msg_type, [])
        for handler in handlers:
            result = handler(data)
            if asyncio.iscoroutine(result):
                await result

    async def _handle_handshake(self, _data: dict[str, Any]) -> None:
        self._connected = True
        log.info("Handshake completat — sessió %s", self._session_id)
        await self.send({
            "type": "handshake_ack",
            "sessionId": self._session_id,
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": ["camera", "viewport", "shutdown"],
        })



