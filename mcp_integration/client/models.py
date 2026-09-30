from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MCPToolResult:
    success: bool
    data: Any = None
    error: str | None = None