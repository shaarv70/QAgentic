from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MCPExecutionOperation:

    tool_name: str

    arguments: dict[str, Any] = field(
        default_factory=dict
    )

    depends_on: list[str] = field(
        default_factory=list
    )


@dataclass(slots=True)
class MCPExecutionPlan:

    executable: bool = True

    reason: str | None = None

    operations: list[MCPExecutionOperation] = field(
        default_factory=list
    )