"""WebSocket bridge between the Python backend and the Three.js frontend.

Responsibilities:
  - Manage the WebSocket lifecycle for a single connected client.
  - Perform the typed handshake (``frontend_ready`` → ``handshake_ack``).
  - Receive ``camera_changed`` and ``viewport_resized`` from the frontend.
  - Send ``set_camera_pose``, ``focus_direction``, and ``shutdown_requested``
    to the frontend.
  - Coordinate clean shutdown (``shutdown_requested`` → ``shutdown_complete``).
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

# Type alias for bridge message handlers
MessageHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


class WebSocketBridge:
    """Server-side half of the Python ↔ Three.js bridge."""

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
        """Set when the frontend sends ``shutdown_complete``."""
        return self._shutdown_event

    def on(self, msg_type: str, handler: MessageHandler) -> None:
        """Register a handler for a specific message type."""
        self._handlers.setdefault(msg_type, []).append(handler)

    async def handle_websocket(
        self, request: aiohttp.web.Request,
    ) -> aiohttp.web.WebSocketResponse:
        """Handle a new WebSocket connection (one at a time)."""
        ws = aiohttp.web.WebSocketResponse(heartbeat=10)
        await ws.prepare(request)
        log.info("WebSocket connected")

        # Only one client at a time
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
                        log.warning("Invalid JSON from frontend: %s", msg.data[:200])
                        continue
                    await self._dispatch(data)
                elif msg.type in (
                    aiohttp.WSMsgType.ERROR,
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.CLOSING,
                ):
                    break
        except Exception:
            log.exception("WebSocket error")
        finally:
            self._connected = False
            self._ws = None
            log.info("WebSocket disconnected")
            # Signal shutdown on disconnect (browser closed)
            self._shutdown_event.set()

        return ws

    async def send(self, msg: dict[str, Any]) -> None:
        """Send a JSON message to the connected frontend."""
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

    async def request_shutdown(self) -> None:
        """Ask the frontend to clean up and confirm with shutdown_complete."""
        await self.send({"type": "shutdown_requested"})

    # ─── Private ──────────────────────────────────────────────────────

    async def _dispatch(self, data: dict[str, Any]) -> None:
        msg_type = data.get("type")
        if not isinstance(msg_type, str):
            log.warning("Message without type: %s", data)
            return

        if msg_type == "frontend_ready":
            await self._handle_handshake(data)
        elif msg_type == "shutdown_complete":
            log.info("Frontend confirmed shutdown")
            self._shutdown_event.set()
        else:
            handlers = self._handlers.get(msg_type, [])
            for handler in handlers:
                result = handler(data)
                if asyncio.iscoroutine(result):
                    await result

    async def _handle_handshake(self, _data: dict[str, Any]) -> None:
        self._connected = True
        log.info("Handshake completed — session %s", self._session_id)
        await self.send({
            "type": "handshake_ack",
            "sessionId": self._session_id,
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": ["camera", "viewport", "shutdown"],
        })
