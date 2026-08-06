"""HTTP + WebSocket server for TerraLab3D.

Serves the compiled frontend as static files and exposes a ``/ws``
endpoint for the bidirectional Python ↔ Three.js bridge.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import aiohttp.web

from .websocket_bridge import WebSocketBridge

log = logging.getLogger("terralab3d.server")


class TerraLabServer:
    """Asyncio-based HTTP/WebSocket server for TerraLab3D."""

    def __init__(
        self,
        dist_dir: Path,
        bridge: WebSocketBridge,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        self._dist_dir = dist_dir
        self._bridge = bridge
        self._host = host
        self._port = port
        self._actual_port = 0
        self._app: aiohttp.web.Application | None = None
        self._runner: aiohttp.web.AppRunner | None = None
        self._site: aiohttp.web.TCPSite | None = None

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._actual_port}"

    @property
    def actual_port(self) -> int:
        return self._actual_port

    async def start(self) -> str:
        """Start the server and return the base URL."""
        self._app = aiohttp.web.Application()
        self._app.router.add_get("/ws", self._bridge.handle_websocket)
        self._app.router.add_get("/", self._serve_index)
        self._app.router.add_static(
            "/", self._dist_dir, show_index=False,
        )

        self._runner = aiohttp.web.AppRunner(
            self._app,
            access_log=None,  # suppress noisy access logs
        )
        await self._runner.setup()

        self._site = aiohttp.web.TCPSite(
            self._runner, self._host, self._port,
        )
        await self._site.start()

        # Resolve actual port (when port=0, OS assigns one)
        for sock in self._site._server.sockets:  # type: ignore[union-attr]
            addr = sock.getsockname()
            self._actual_port = addr[1]
            break

        log.info("Server listening on %s", self.url)
        return self.url

    async def stop(self) -> None:
        """Gracefully shut down the server."""
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
        log.info("Server stopped")

    async def _serve_index(
        self, request: aiohttp.web.Request,
    ) -> aiohttp.web.FileResponse:
        """Serve index.html for the root path."""
        return aiohttp.web.FileResponse(self._dist_dir / "index.html")
