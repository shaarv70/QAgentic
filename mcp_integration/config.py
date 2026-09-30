from dataclasses import dataclass, field


@dataclass(frozen=True)
class MCPServerConfig:
    """
    Configuration for an MCP server.

    Transport-specific connection information is kept here,
    while connection and execution logic remain in MCPClient.
    """

    name: str

    transport: str = "streamable-http"

    url: str | None = None

    headers: dict[str, str] = field(default_factory=dict)

    enabled: bool = True

    # Retained for compatibility with MCP servers that may
    # expose stdio transport, but not used by our primary path.
    command: str | None = None

    args: list[str] = field(default_factory=list)

    environment: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:

        if not self.name.strip():

            raise ValueError("MCP server name cannot be empty.")

        if self.transport not in {"streamable-http","stdio",}:

            raise ValueError(f"Unsupported MCP transport: {self.transport}")

        if self.transport == "streamable-http" and not self.url:

            raise ValueError("URL is required for streamable-http transport.")

        if self.transport == "stdio" and not self.command:

            raise ValueError("Command is required for stdio transport.")