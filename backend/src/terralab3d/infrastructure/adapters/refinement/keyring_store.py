"""OS Keyring credential store adapter."""

from __future__ import annotations

import logging

from terralab3d.application.ports.authentication import CredentialStorePort
from terralab3d.domain.refinement.authentication import CdseCredentials

logger = logging.getLogger(__name__)


class OsCredentialStoreAdapter(CredentialStorePort):
    """Stores credentials securely using the native OS keychain/credential manager."""

    def __init__(self, service_name: str = "TerraLab3D-CDSE") -> None:
        self._service_name = service_name
        
        # We try to import keyring and check if it has a working backend
        self._keyring = None
        try:
            import keyring
            # Smoke test
            if keyring.get_keyring():
                self._keyring = keyring
        except ImportError:
            logger.warning("MGP: [OsCredentialStoreAdapter] 'keyring' module not installed. Secure storage disabled.")
        except Exception as exc:
            logger.warning("MGP: [OsCredentialStoreAdapter] Failed to initialize keyring: %s", exc)

    def save_credentials(self, credentials: CdseCredentials) -> None:
        if not self._keyring:
            return
            
        try:
            # We use a fixed account name (e.g. the username) so we can retrieve it later
            # Wait, if we use the username as the account name, we need to know the username to retrieve it!
            # Since CDSE only has one active account for TerraLab3D at a time, we can store the username 
            # as a secondary credential, or just use a fixed account name "default" for the JSON payload,
            # or store the password under the username, and store the username under a "current_user" key.
            # Let's just use "default_user" to store the username, and the username to store the password.
            
            self._keyring.set_password(self._service_name, "default_user", credentials.username)
            self._keyring.set_password(self._service_name, credentials.username, credentials.password)
            logger.debug("MGP: [OsCredentialStoreAdapter] Credentials saved securely")
        except Exception as exc:
            logger.error("MGP: [OsCredentialStoreAdapter] Failed to save credentials: %s", exc)

    def get_credentials(self) -> CdseCredentials | None:
        if not self._keyring:
            return None
            
        try:
            username = self._keyring.get_password(self._service_name, "default_user")
            if not username:
                return None
                
            password = self._keyring.get_password(self._service_name, username)
            if not password:
                return None
                
            return CdseCredentials(username=username, password=password)
        except Exception as exc:
            logger.error("MGP: [OsCredentialStoreAdapter] Failed to get credentials: %s", exc)
            return None

    def clear_credentials(self) -> None:
        if not self._keyring:
            return
            
        try:
            username = self._keyring.get_password(self._service_name, "default_user")
            if username:
                try:
                    self._keyring.delete_password(self._service_name, username)
                except Exception:
                    pass
            try:
                self._keyring.delete_password(self._service_name, "default_user")
            except Exception:
                pass
            logger.debug("MGP: [OsCredentialStoreAdapter] Credentials cleared")
        except Exception as exc:
            logger.error("MGP: [OsCredentialStoreAdapter] Failed to clear credentials: %s", exc)
