from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExecutionServerConfig:
    """
    Describes an execution server available to QAgentic.

    An execution server may represent:

        - a test runner
        - a browser automation server
        - a mobile automation server
        - an API automation server
        - another execution backend

    This class contains configuration only.
    It does not execute anything.

    A server may expose multiple operations/tools, therefore
    tool_name is optional at the server configuration level.
    """

    name: str

    category: str

    provider_type: str

    server_name: str | None = None

    tool_name: str | None = None

    frameworks: tuple[str, ...] = field(default_factory=tuple)

    enabled: bool = True

    priority: int = 100

    def __post_init__(self) -> None:

        if not self.name.strip():
            raise ValueError(
                "Execution server name cannot be empty."
            )

        if not self.category.strip():
            raise ValueError(
                "Execution server category cannot be empty."
            )

        if not self.provider_type.strip():
            raise ValueError(
                "Execution server provider type cannot be empty."
            )

        if self.provider_type == "mcp":

            if not self.server_name:
                raise ValueError(
                    "server_name is required for MCP execution servers."
                )