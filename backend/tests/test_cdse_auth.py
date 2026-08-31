import asyncio
import time
import pytest
from aiohttp import web

from terralab3d.application.refinement.auth_coordinator import AuthenticationCoordinator
from terralab3d.application.ports.authentication import CdseAuthenticationPort, CredentialStorePort, CdseAuthenticationError
from terralab3d.domain.refinement.authentication import CdseCredentials, CdseSession
from terralab3d.infrastructure.adapters.refinement.providers.cdse_identity import (
    CdseIdentityAdapter,
)

class MockAuthPort(CdseAuthenticationPort):
    def __init__(self):
        self.auth_calls = 0
        self.refresh_calls = 0
        self.fail_auth = False
        self.fail_refresh = False

    async def authenticate(self, credentials):
        self.auth_calls += 1
        if self.fail_auth:
            raise CdseAuthenticationError("Invalid credentials")
        return CdseSession("access_1", time.time() + 3600, "refresh_1", time.time() + 3600)

    async def refresh(self, refresh_token):
        self.refresh_calls += 1
        if self.fail_refresh:
            raise CdseAuthenticationError("Invalid refresh token")
        return CdseSession("access_2", time.time() + 3600, "refresh_2", time.time() + 3600)

class MockCredentialStore(CredentialStorePort):
    def __init__(self):
        self.creds = None
        self.clear_calls = 0
        self.save_calls = 0

    def save_credentials(self, credentials):
        self.save_calls += 1
        self.creds = credentials

    def get_credentials(self):
        return self.creds

    def clear_credentials(self):
        self.clear_calls += 1
        self.creds = None


def test_get_valid_token_interactive():
    async def _test():
        auth_port = MockAuthPort()
        store = MockCredentialStore()
        
        cb_called = False
        def cb():
            nonlocal cb_called
            cb_called = True

        coordinator = AuthenticationCoordinator(auth_port, store, cb)
        
        task = asyncio.create_task(coordinator.get_valid_token(interactive=True))
        
        await asyncio.sleep(0.01)
        assert cb_called
        
        await coordinator.submit_credentials(CdseCredentials("u", "p"), remember=True)
        
        token = await task
        assert token == "access_1"
        assert store.save_calls == 1
        assert store.creds is not None

    asyncio.run(_test())


def test_transparent_refresh():
    async def _test():
        auth_port = MockAuthPort()
        store = MockCredentialStore()
        coordinator = AuthenticationCoordinator(auth_port, store, lambda: None)
        
        coordinator._session = CdseSession("old", time.time() - 10, "refresh_1", time.time() + 3600)
        
        token = await coordinator.get_valid_token(interactive=True)
        assert token == "access_2"
        assert auth_port.refresh_calls == 1
        assert auth_port.auth_calls == 0

    asyncio.run(_test())


def test_concurrent_auth_only_prompts_once():
    async def _test():
        auth_port = MockAuthPort()
        store = MockCredentialStore()
        
        cb_calls = 0
        def cb():
            nonlocal cb_calls
            cb_calls += 1

        coordinator = AuthenticationCoordinator(auth_port, store, cb)
        
        task1 = asyncio.create_task(coordinator.get_valid_token(interactive=True))
        task2 = asyncio.create_task(coordinator.get_valid_token(interactive=True))
        
        await asyncio.sleep(0.01)
        assert cb_calls == 1
        
        await coordinator.submit_credentials(CdseCredentials("u", "p"), remember=False)
        
        t1 = await task1
        t2 = await task2
        assert t1 == "access_1"
        assert t2 == "access_1"
        assert auth_port.auth_calls == 1

    asyncio.run(_test())


def test_cdse_identity_sends_optional_totp_as_form_data():
    async def _test():
        received = {}

        async def token(request: web.Request) -> web.Response:
            received.update(await request.post())
            return web.json_response(
                {
                    "access_token": "access",
                    "expires_in": 3600,
                    "refresh_token": "refresh",
                    "refresh_expires_in": 7200,
                }
            )

        app = web.Application()
        app.router.add_post("/token", token)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        try:
            adapter = CdseIdentityAdapter(f"http://127.0.0.1:{port}/token")
            session = await adapter.authenticate(
                CdseCredentials("user@example.test", "secret", "123456")
            )
        finally:
            await runner.cleanup()

        assert session.access_token == "access"
        assert received == {
            "client_id": "cdse-public",
            "grant_type": "password",
            "username": "user@example.test",
            "password": "secret",
            "totp": "123456",
        }

    asyncio.run(_test())


def test_cdse_identity_raises_auth_error_on_403_forbidden():
    async def _test():
        async def token(request: web.Request) -> web.Response:
            return web.json_response(
                {"error": "access_denied", "error_description": "User forbidden"},
                status=403,
            )

        app = web.Application()
        app.router.add_post("/token", token)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        try:
            adapter = CdseIdentityAdapter(f"http://127.0.0.1:{port}/token")
            with pytest.raises(CdseAuthenticationError) as exc_info:
                await adapter.authenticate(CdseCredentials("user@example.test", "wrong"))
            assert "403" in str(exc_info.value)
            assert "User forbidden" in str(exc_info.value)
        finally:
            await runner.cleanup()

    asyncio.run(_test())


if __name__ == "__main__":
    test_get_valid_token_interactive()
    test_transparent_refresh()
    test_concurrent_auth_only_prompts_once()
    test_cdse_identity_raises_auth_error_on_403_forbidden()
    print("ALL TESTS PASSED")
