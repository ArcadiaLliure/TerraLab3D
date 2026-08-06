"""Models de domini tipats per a la capacitat progrés, errors, mode de reserva i estat visible."""


from dataclasses import dataclass
from enum import Enum

class IssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

@dataclass(frozen=True, slots=True)
class OperationStatus:
    operation_id: str
    progress_fraction: float | None
    state: str
    message_key: str

@dataclass(frozen=True, slots=True)
class UserFacingIssue:
    code: str
    severity: IssueSeverity
    message_key: str
    recoverable: bool
