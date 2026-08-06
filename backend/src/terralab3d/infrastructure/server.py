"""Servidor HTTP + WebSocket per a TerraLab3D.

Serveix el frontend compilat com a fitxers estàtics i exposa un punt final ``/ws``
per al pont bidireccional Python ↔ Three.js.
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
    """Servidor HTTP/WebSocket basat en asyncio per a TerraLab3D."""

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
        """Inicia el servidor i retorna l'URL base."""
        self._app = aiohttp.web.Application()
        self._app.router.add_get("/ws", self._bridge.handle_websocket)
        self._app.router.add_get("/", self._serve_index)
        self._app.router.add_static(
            "/", self._dist_dir, show_index=False,
        )

        self._runner = aiohttp.web.AppRunner(
            self._app,
            access_log=None,  # suprimeix els registres d'accés sorollosos
        )
        await self._runner.setup()

        self._site = aiohttp.web.TCPSite(
            self._runner, self._host, self._port,
        )
        await self._site.start()

        # Resol el port real (quan port=0, el SO n'assigna un)
        for sock in self._site._server.sockets:  # type: ignore[union-attr]
            addr = sock.getsockname()
            self._actual_port = addr[1]
            break

        log.info("Servidor escoltant a %s", self.url)
        return self.url

    async def stop(self) -> None:
        """Atura el servidor de manera ordenada."""
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
        log.info("Servidor aturat")

    async def _serve_index(
        self, request: aiohttp.web.Request,
    ) -> aiohttp.web.FileResponse:
        """Serveix index.html per a la ruta arrel."""
        return aiohttp.web.FileResponse(self._dist_dir / "index.html")



