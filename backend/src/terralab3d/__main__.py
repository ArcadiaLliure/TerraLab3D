"""TerraLab3D application entry point.

Usage::

    python -m terralab3d

Sequence:
  1. Bundle the TypeScript frontend (esbuild, once).
  2. Start the aiohttp server (HTTP static + WebSocket bridge).
  3. Open the system browser.
  4. Wait for the bridge handshake.
  5. Listen for camera_changed, viewport_resized, etc.
  6. On Ctrl-C or browser close → request frontend shutdown → exit cleanly.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
import webbrowser
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("terralab3d")


async def run() -> int:
    """Main async entry point."""
    from terralab3d.infrastructure.bundler import bundle_frontend
    from terralab3d.infrastructure.server import TerraLabServer
    from terralab3d.infrastructure.websocket_bridge import WebSocketBridge

    # ── 1. Bundle frontend ────────────────────────────────────────────
    try:
        dist_dir = bundle_frontend()
    except Exception as exc:
        log.error("Frontend build failed: %s", exc)
        return 1

    # ── 2. Create bridge & server ─────────────────────────────────────
    bridge = WebSocketBridge()
    server = TerraLabServer(dist_dir, bridge)

    # Register bridge message handlers
    bridge.on("camera_changed", _on_camera_changed)
    bridge.on("viewport_resized", _on_viewport_resized)
    bridge.on("bridge_error", _on_bridge_error)

    # ── 3. Start server ──────────────────────────────────────────────
    url = await server.start()
    log.info("TerraLab3D ready at %s", url)

    # ── 4. Open browser ──────────────────────────────────────────────
    webbrowser.open(url)

    # ── 5. Wait for shutdown ─────────────────────────────────────────
    # Set up Ctrl-C handler
    loop = asyncio.get_running_loop()
    shutdown_requested = asyncio.Event()

    def handle_signal() -> None:
        log.info("Signal received — shutting down")
        shutdown_requested.set()

    # Register signal handlers
    try:
        loop.add_signal_handler(signal.SIGINT, handle_signal)
        loop.add_signal_handler(signal.SIGTERM, handle_signal)
    except NotImplementedError:
        # Windows doesn't support add_signal_handler for all signals
        # Fall back to signal.signal for SIGINT
        signal.signal(signal.SIGINT, lambda *_: handle_signal())

    # Schedule a demo camera pose after 3 seconds (proves bidirectionality)
    async def demo_camera_command() -> None:
        """Wait for handshake, then send a test camera pose to prove
        Python → Frontend communication works."""
        while not bridge.connected:
            await asyncio.sleep(0.1)
        log.info("Bridge connected — session %s", bridge.session_id)
        await asyncio.sleep(3)
        if bridge.connected:
            log.info("Sending set_camera_pose to verify bidirectional bridge")
            await bridge.send_set_camera_pose(
                az=180.0, alt=30.0, fov=60.0, transition_ms=1200,
            )

    demo_task = asyncio.create_task(demo_camera_command())

    # Wait for either Ctrl-C or browser disconnect
    done, _ = await asyncio.wait(
        [
            asyncio.create_task(shutdown_requested.wait()),
            asyncio.create_task(bridge.shutdown_event.wait()),
        ],
        return_when=asyncio.FIRST_COMPLETED,
    )

    # ── 6. Clean shutdown ─────────────────────────────────────────────
    log.info("Initiating shutdown...")

    # Cancel the demo task if still running
    demo_task.cancel()
    try:
        await demo_task
    except asyncio.CancelledError:
        pass

    # Ask frontend to clean up (if still connected)
    if bridge.connected:
        await bridge.request_shutdown()
        try:
            await asyncio.wait_for(bridge.shutdown_event.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            log.warning("Frontend did not confirm shutdown within 3s")

    await server.stop()
    log.info("TerraLab3D shut down cleanly")
    return 0


# ─── Bridge message handlers ─────────────────────────────────────────

async def _on_camera_changed(data: dict[str, Any]) -> None:
    """Receive camera pose updates from the frontend (throttled)."""
    log.debug(
        "Camera: az=%.1f° alt=%.1f° fov=%.1f°",
        data.get("azimuthDeg", 0),
        data.get("altitudeDeg", 0),
        data.get("horizontalFovDeg", 0),
    )


async def _on_viewport_resized(data: dict[str, Any]) -> None:
    log.info(
        "Viewport resized: %dx%d @%.1fx",
        data.get("widthPx", 0),
        data.get("heightPx", 0),
        data.get("devicePixelRatio", 1),
    )


async def _on_bridge_error(data: dict[str, Any]) -> None:
    log.error(
        "Bridge error from frontend: [%s] %s",
        data.get("code", "?"),
        data.get("message", "?"),
    )


def main() -> int:
    """Synchronous entry point for ``python -m terralab3d``."""
    try:
        return asyncio.run(run())
    except KeyboardInterrupt:
        log.info("Interrupted")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
