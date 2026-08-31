"""Authentication ports for external identity providers and credential storage."""

from __future__ import annotations

import abc

from terralab3d.domain.refinement.authentication import CdseCredentials, CdseSession


class CdseAuthenticationError(Exception):
    """Raised when authentication with CDSE fails."""
    pass


class CdseAuthenticationPort(abc.ABC):
    """Port for authenticating against the Copernicus Data Space Ecosystem (CDSE)."""

    @abc.abstractmethod
    async def authenticate(self, credentials: CdseCredentials) -> CdseSession:
        """
        Authenticate using username and password (Resource Owner Password Credentials).
        
        :raises CdseAuthenticationError: If the credentials are invalid or CDSE rejects them.
        """
        pass

    @abc.abstractmethod
    async def refresh(self, refresh_token: str) -> CdseSession:
        """
        Refresh an existing session using a refresh token.
        
        :raises CdseAuthenticationError: If the refresh token is invalid or expired.
        """
        pass


class CredentialStorePort(abc.ABC):
    """Port for securely storing and retrieving credentials in the OS."""

    @abc.abstractmethod
    def save_credentials(self, credentials: CdseCredentials) -> None:
        """Securely store the credentials."""
        pass

    @abc.abstractmethod
    def get_credentials(self) -> CdseCredentials | None:
        """Retrieve the credentials if they exist."""
        pass

    @abc.abstractmethod
    def clear_credentials(self) -> None:
        """Remove the credentials from the store."""
        pass
