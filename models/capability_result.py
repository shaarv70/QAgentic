from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CapabilityResult:
    status: str
    data: Any = None
    error: str | None = None
    retryable: bool = True