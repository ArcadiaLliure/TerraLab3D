"""CDSE HTTP authentication adapter."""

from __future__ import annotations

import time

import aiohttp

from terralab3d.application.ports.authentication import CdseAuthenticationError, CdseAuthenticationPort
from terralab3d.domain.refinement.authentication import CdseCredentials, CdseSession


class CdseIdentityAdapter(CdseAuthenticationPort):
    """Authenticates against the Copernicus Keycloak instance."""

    def __init__(self, token_url: str = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token") -> None:
        self._token_url = token_url
        self._client_id = "cdse-public"

    async def _post_token(self, data: dict[str, str]) -> CdseSession:
        timeout = aiohttp.ClientTimeout(total=30.0)
        now = time.time()
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(self._token_url, data=data) as response:
                    if response.status != 200:
                        try:
                            error_payload = await response.json()
                            error_desc = error_payload.get("error_description", error_payload.get("error", "Unknown error"))
                        except Exception:
                            error_desc = await response.text()
                        
                        # 4xx client errors (400, 401, 403, etc.) are auth/credential failures
                        if 400 <= response.status < 500:
                            raise CdseAuthenticationError(f"CDSE Authentication failed ({response.status}): {error_desc}")
                        else:
                            # 5xx Server errors -> handled as network/server errors
                            response.raise_for_status()

                    payload = await response.json()
                    
                    access_token = payload.get("access_token")
                    expires_in = payload.get("expires_in")
                    
                    if not access_token or not isinstance(expires_in, int):
                        raise CdseAuthenticationError("Invalid token response from CDSE")

                    return CdseSession.from_cdse_response(
                        access_token=access_token,
                        expires_in=expires_in,
                        refresh_token=payload.get("refresh_token"),
                        refresh_expires_in=payload.get("refresh_expires_in"),
                        now=now,
                    )
            except aiohttp.ClientError:
                # Wrap network errors, but these aren't credential failures, they are network failures.
                # However, the port signature expects exceptions. We let ClientError propagate or wrap it.
                # Since CdseAuthenticationError implies bad credentials, we should let ClientError propagate
                # so the coordinator knows it's a network issue and can retry later instead of clearing credentials.
                raise

    async def authenticate(self, credentials: CdseCredentials) -> CdseSession:
        data = {
            "client_id": self._client_id,
            "grant_type": "password",
            "username": credentials.username,
            "password": credentials.password,
        }
        if credentials.totp:
            data["totp"] = credentials.totp
        return await self._post_token(data)

    async def refresh(self, refresh_token: str) -> CdseSession:
        return await self._post_token({
            "client_id": self._client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        })
