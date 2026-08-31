"""Coordinator for CDSE authentication and session state."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from terralab3d.application.ports.authentication import (
    CdseAuthenticationError,
    CdseAuthenticationPort,
    CredentialStorePort,
)
from terralab3d.domain.refinement.authentication import CdseCredentials, CdseSession

logger = logging.getLogger(__name__)


class AuthenticationRequiredError(Exception):
    """Raised when authentication is required but interactive mode is off or cancelled."""
    pass


class AuthenticationCoordinator:
    """Manages the CDSE session lifecycle, refresh logic, and credential prompts."""

    def __init__(
        self,
        auth_port: CdseAuthenticationPort,
        credential_store: CredentialStorePort,
        request_credentials_callback: Callable[[], None],
    ) -> None:
        self._auth_port = auth_port
        self._credential_store = credential_store
        self._request_credentials_callback = request_credentials_callback
        
        self._session: CdseSession | None = None
        self._auth_lock = asyncio.Lock()
        self._pending_auth_future: asyncio.Future[bool] | None = None

    def invalidate_session(self) -> None:
        """Clear the current session (e.g., when a 401 is received)."""
        logger.debug("MGP: [AuthenticationCoordinator] Session invalidated")
        self._session = None

    def forget_credentials(self) -> None:
        """Clear credentials from the OS store and invalidate session."""
        self.invalidate_session()
        self._credential_store.clear_credentials()

    async def get_valid_token(self, interactive: bool = True) -> str:
        """
        Get a valid CDSE access token.
        
        If the token is expired, attempts to refresh.
        If refresh fails, attempts to use stored credentials.
        If stored credentials fail or don't exist, and interactive is True,
        suspends and requests credentials from the UI.
        
        :raises AuthenticationRequiredError: If no valid token can be obtained.
        """
        async with self._auth_lock:
            if self._session and self._session.has_valid_access_token():
                return self._session.access_token

            # Try refresh
            if self._session and self._session.can_refresh():
                try:
                    logger.debug("MGP: [AuthenticationCoordinator] Attempting token refresh")
                    self._session = await self._auth_port.refresh(self._session.refresh_token)
                    return self._session.access_token
                except CdseAuthenticationError as exc:
                    logger.warning("MGP: [AuthenticationCoordinator] Refresh failed: %s", exc)
                    self._session = None
                except Exception as exc:
                    # Network error during refresh, do not invalidate session yet, but we can't return a token
                    raise AuthenticationRequiredError(f"Network error during refresh: {exc}") from exc

            # Try stored credentials
            stored_creds = self._credential_store.get_credentials()
            if stored_creds:
                try:
                    logger.debug("MGP: [AuthenticationCoordinator] Attempting auth with stored credentials")
                    self._session = await self._auth_port.authenticate(stored_creds)
                    return self._session.access_token
                except CdseAuthenticationError as exc:
                    logger.warning("MGP: [AuthenticationCoordinator] Stored credentials rejected: %s", exc)
                    self._credential_store.clear_credentials()
                except Exception as exc:
                    raise AuthenticationRequiredError(f"Network error during auth: {exc}") from exc

        # If we reach here, we need new credentials
        if not interactive:
            raise AuthenticationRequiredError("Authentication required, but interactive mode is off")

        # Suspend and ask UI
        return await self._suspend_for_interactive_auth()

    async def _suspend_for_interactive_auth(self) -> str:
        """Suspend execution until credentials are provided via UI."""
        # We need to coordinate multiple waiters. If an auth is already pending, just wait for it.
        future = None
        async with self._auth_lock:
            # Re-check if another task just succeeded while we were acquiring the lock
            if self._session and self._session.has_valid_access_token():
                return self._session.access_token

            if self._pending_auth_future is None:
                self._pending_auth_future = asyncio.Future()
                # Trigger the callback to notify the UI
                self._request_credentials_callback()
            
            future = self._pending_auth_future

        # Wait outside the lock so we don't block other tasks from also waiting or resolving
        try:
            success = await future
            if not success:
                raise AuthenticationRequiredError("Authentication cancelled by user")
            
            async with self._auth_lock:
                if not self._session or not self._session.has_valid_access_token():
                    raise AuthenticationRequiredError("Authentication completed but no valid session found")
                return self._session.access_token
        except asyncio.CancelledError:
            # If this specific task is cancelled, we shouldn't fail the global future
            raise

    async def submit_credentials(self, credentials: CdseCredentials | None, remember: bool) -> None:
        """
        Called by the UI when the user submits or cancels the login dialog.
        
        If credentials is None, the user cancelled.
        """
        async with self._auth_lock:
            future = self._pending_auth_future
            self._pending_auth_future = None

        if not credentials:
            if future and not future.done():
                future.set_result(False)
            return

        try:
            logger.debug("MGP: [AuthenticationCoordinator] Attempting interactive auth")
            session = await self._auth_port.authenticate(credentials)
            
            async with self._auth_lock:
                self._session = session
                if remember:
                    self._credential_store.save_credentials(credentials)
                else:
                    # Ensure we don't have stale credentials if the user explicitly chose not to remember this time
                    self._credential_store.clear_credentials()
            
            if future and not future.done():
                future.set_result(True)
        except Exception as exc:
            logger.error("MGP: [AuthenticationCoordinator] Interactive auth failed: %s", exc)
            if future and not future.done():
                # We could set exception, but returning False allows the waiters to raise a clean AuthenticationRequiredError
                future.set_exception(exc)
            raise
