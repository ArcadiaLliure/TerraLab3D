import asyncio

from terralab3d.infrastructure.websocket_bridge import WebSocketBridge


def test_frontend_ready_is_dispatched_once_per_connection() -> None:
    bridge = WebSocketBridge()
    ready_notifications = 0

    def on_ready(_message: dict[str, object]) -> None:
        nonlocal ready_notifications
        ready_notifications += 1

    bridge.on("frontend_ready", on_ready)

    async def scenario() -> None:
        handshake_complete = False
        message = {"type": "frontend_ready", "protocolVersion": 2}
        handshake_complete = await bridge._dispatch_connection_message(
            message,
            handshake_complete=handshake_complete,
        )
        handshake_complete = await bridge._dispatch_connection_message(
            message,
            handshake_complete=handshake_complete,
        )
        assert handshake_complete

    asyncio.run(scenario())
    assert ready_notifications == 1
