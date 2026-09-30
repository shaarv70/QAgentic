from mcp_integration.config import MCPServerConfig
from registries.base_registry import BaseRegistry


class MCPServerRegistry(BaseRegistry[MCPServerConfig]):

    def __init__(self):
        super().__init__()
        self._register_default_servers()

    def _register_default_servers(self) -> None:

        self.register(
            "github",
            MCPServerConfig(
                name="github",
                transport="streamable-http",
                url="https://api.githubcopilot.com/mcp/",
                enabled=True,
                headers={},
            ),
        )
        self.register(
            "selenium",
            MCPServerConfig(
                name="selenium",
                transport="streamable-http",
                url="http://127.0.0.1:3345/mcp",
                enabled=True,
                headers={},
            ),
        )

        # Future default MCP servers:
        #
        # self.register(
        #     "playwright",
        #     MCPServerConfig(...)
        # )
        #
        # self.register(
        #     "appium",
        #     MCPServerConfig(...)
        # )