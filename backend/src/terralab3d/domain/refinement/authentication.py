"""Copernicus Data Space Ecosystem (CDSE) authentication models."""

from __future__ import annotations

import dataclasses
import time
from typing import Self


@dataclasses.dataclass(frozen=True)
class CdseCredentials:
    """Ephemeral credentials used for authenticating with CDSE."""
    username: str
    password: str
    totp: str | None = None

    def __repr__(self) -> str:
        return (
            f"CdseCredentials(username={self.username!r}, password='***', "
            f"totp={'***' if self.totp else None})"
        )


@dataclasses.dataclass(frozen=True)
class CdseSession:
    """
    Ephemeral session state holding the CDSE tokens.
    
    Tokens must never be persisted to disk. The `refresh_token` allows
    renewing the session without prompting the user for credentials again.
    """
    access_token: str
    access_token_expires_at: float
    refresh_token: str | None
    refresh_token_expires_at: float | None

    def has_valid_access_token(self, leeway_seconds: float = 30.0) -> bool:
        """Return True if the access token is valid and not immediately expiring."""
        return time.time() < (self.access_token_expires_at - leeway_seconds)

    def can_refresh(self, leeway_seconds: float = 30.0) -> bool:
        """Return True if there is a refresh token and it is still valid."""
        if not self.refresh_token or not self.refresh_token_expires_at:
            return False
        return time.time() < (self.refresh_token_expires_at - leeway_seconds)

    @classmethod
    def from_cdse_response(
        cls,
        access_token: str,
        expires_in: int,
        refresh_token: str | None = None,
        refresh_expires_in: int | None = None,
        now: float | None = None,
    ) -> Self:
        """Create a session using the expiration times returned by the server."""
        if now is None:
            now = time.time()
        return cls(
            access_token=access_token,
            access_token_expires_at=now + expires_in,
            refresh_token=refresh_token,
            refresh_token_expires_at=now + refresh_expires_in if refresh_expires_in is not None else None,
        )

    def __repr__(self) -> str:
        return (
            f"CdseSession("
            f"valid_access={self.has_valid_access_token()}, "
            f"can_refresh={self.can_refresh()})"
        )
