from __future__ import annotations

import asyncio
from pathlib import Path

from aiohttp import ClientSession

from terralab3d.infrastructure.server import TerraLabServer
from terralab3d.infrastructure.websocket_bridge import WebSocketBridge


def test_live_frontend_files_are_never_reused_from_an_old_app_session(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<script src='/bundle.js'></script>", encoding="utf-8")
    (tmp_path / "bundle.js").write_text("console.log('current')", encoding="utf-8")
    (tmp_path / "bundle.css").write_text("body{}", encoding="utf-8")

    async def scenario() -> None:
        server = TerraLabServer(tmp_path, WebSocketBridge(), host="127.0.0.1", port=0)
        await server.start()
        try:
            async with ClientSession() as client:
                for path in ("/", "/bundle.js", "/bundle.css"):
                    async with client.get(f"{server.url}{path}") as response:
                        assert response.status == 200
                        assert response.headers["Cache-Control"] == "no-store"
        finally:
            await server.stop()

    asyncio.run(scenario())
