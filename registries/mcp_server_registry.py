import os

from mcp_integration.config import MCPServerConfig
from registries.base_registry import BaseRegistry


class MCPServerRegistry(BaseRegistry[MCPServerConfig]):

    def __init__(self):
        super().__init__()
        self._register_default_servers()

    def _register_default_servers(self) -> None:

        # ----------------------------------------------------------
        # GitHub MCP
        # Two transport options controlled by GITHUB_MCP_TRANSPORT:
        #   stdio (default) — npx @modelcontextprotocol/server-github
        #                     requires GITHUB_PERSONAL_ACCESS_TOKEN
        #   streamable-http — GitHub Copilot MCP endpoint
        #                     requires Copilot auth (no PAT needed)
        # ----------------------------------------------------------
        github_transport = os.getenv("GITHUB_MCP_TRANSPORT", "stdio")

        if github_transport == "streamable-http":
            github_url = os.getenv(
                "GITHUB_COPILOT_MCP_URL",
                "https://api.githubcopilot.com/mcp/",
            )
            self.register(
                "github",
                MCPServerConfig(
                    name="github",
                    transport="streamable-http",
                    url=github_url,
                    enabled=True,
                ),
            )
        else:
            pat = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
            self.register(
                "github",
                MCPServerConfig(
                    name="github",
                    transport="stdio",
                    command="npx",
                    args=["-y", "@modelcontextprotocol/server-github"],
                    environment={"GITHUB_PERSONAL_ACCESS_TOKEN": pat} if pat else {},
                    enabled=bool(pat),
                ),
            )

        # ----------------------------------------------------------
        # Selenium MCP (local streamable-http server)
        # ----------------------------------------------------------
        self.register(
            "selenium",
            MCPServerConfig(
                name="selenium",
                transport="streamable-http",
                url="http://127.0.0.1:3345/mcp",
                enabled=True,
            ),
        )

        # ----------------------------------------------------------
        # Playwright MCP
        # Launched via npx @playwright/mcp — runs headless by default.
        # PLAYWRIGHT_MCP_ENABLED=false  → disables the server entirely
        # PLAYWRIGHT_MCP_HEADLESS=false → runs headed (shows browser)
        # ----------------------------------------------------------
        playwright_enabled = (
            os.getenv("PLAYWRIGHT_MCP_ENABLED", "true").lower() != "false"
        )
        playwright_headless = (
            os.getenv("PLAYWRIGHT_MCP_HEADLESS", "true").lower() != "false"
        )

        # Pin to an installed version so npx skips the npm registry check
        # and starts in ~2s instead of ~12s.  Update this when upgrading.
        playwright_args = ["-y", "@playwright/mcp@0.0.83"]
        if playwright_headless:
            playwright_args.append("--headless")

        self.register(
            "playwright",
            MCPServerConfig(
                name="playwright",
                transport="stdio",
                command="npx",
                args=playwright_args,
                enabled=playwright_enabled,
            ),
        )
