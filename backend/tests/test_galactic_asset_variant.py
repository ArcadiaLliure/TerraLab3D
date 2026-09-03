from __future__ import annotations

import asyncio
from pathlib import Path

import aiohttp
import pytest

from terralab3d.domain.identifiers import ResourceId, VariantId
from terralab3d.domain.resources.models import ResourceInstallState
from terralab3d.infrastructure.adapters.file_assets.galactic import ManagedGalacticAssets
from terralab3d.infrastructure.resources.installation_repository import (
    ResourceInstallationRepository,
)
from terralab3d.infrastructure.server import TerraLabServer
from terralab3d.infrastructure.websocket_bridge import WebSocketBridge


def test_server_streams_the_requested_ready_galactic_variant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root = tmp_path / "library"
    monkeypatch.setenv("TERRALAB_DATA_ROOT", str(data_root))
    repository = ResourceInstallationRepository()
    managed_dir = data_root / "data" / "sky" / "milky-way"
    managed_dir.mkdir(parents=True)
    texture_4k = managed_dir / "milkyway_2020_4k.exr"
    texture_16k = managed_dir / "milkyway_2020_16k.exr"
    texture_4k.write_bytes(b"4k")
    texture_16k.write_bytes(b"16k")

    for variant_id, texture in (("16k", texture_16k), ("4k", texture_4k)):
        repository.set_resource_state(
            ResourceId("sky.milky_way"),
            ResourceInstallState.READY,
            VariantId(variant_id),
            resolved_path=str(texture),
            manifest_data={"renderPath": str(texture)},
        )

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("ok", encoding="utf-8")

    async def scenario() -> None:
        server = TerraLabServer(
            dist,
            WebSocketBridge(),
            galactic_assets=ManagedGalacticAssets(repository),
            host="127.0.0.1",
            port=0,
        )
        await server.start()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{server.url}/managed-galactic-assets/sky.milky_way?variant=4k"
                ) as response:
                    assert response.status == 200
                    assert await response.read() == b"4k"

                async with session.get(
                    f"{server.url}/managed-galactic-assets/sky.milky_way?variant=32k"
                ) as response:
                    assert response.status == 404
        finally:
            await server.stop()

    asyncio.run(scenario())
