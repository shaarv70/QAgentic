from typing import Any
from mcp_integration.catalog.mcp_tool_catalog import MCPToolCatalog
from mcp_integration.client.mcp_client import MCPClient
from mcp_integration.config import MCPServerConfig
from registries.mcp_server_registry import MCPServerRegistry
from mcp_integration.auth.credential_provider import CredentialProvider
from mcp_integration.guardrails.mcp_guardrail import MCPGuardrail


class MCPToolExecutor:
    """
    Generic execution boundary between QAgentic capabilities
    and external MCP servers.

    Responsibilities:
        - Resolve an MCP server from MCPServerRegistry.
        - Create an MCP client for that server.
        - Connect to the MCP server.
        - Discover/validate the requested tool.
        - Invoke the MCP tool.
        - Close the MCP client.

    This class does not contain server-specific tool logic.
    """

    def __init__(self, server_registry: MCPServerRegistry,credential_provider: CredentialProvider,tool_catalog: MCPToolCatalog,
    guardrail: MCPGuardrail,):

        self.server_registry = server_registry
        self.credential_provider = credential_provider
        self.tool_catalog = tool_catalog
        self.guardrail = guardrail


    async def execute(
    self,
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    ):
        """
        Execute a tool exposed by a registered MCP server.
        """

        # --------------------------------------------------
        # 1. Ensure tool is discovered
        # --------------------------------------------------

        await self._ensure_tool_discovered(
            server_name=server_name,
            tool_name=tool_name,
        )

        # --------------------------------------------------
        # 2. Validate tool against guardrails
        # --------------------------------------------------

        self.guardrail.validate(
            server_name=server_name,
            tool_name=tool_name,
        )

        # --------------------------------------------------
        # 3. Resolve server configuration
        # --------------------------------------------------

        config: MCPServerConfig = self.server_registry.get(
            server_name
        )

        client = MCPClient(
            config=config,
            credential_provider=self.credential_provider,
        )

        # --------------------------------------------------
        # 4. Execute
        # --------------------------------------------------

        try:

            await client.connect()

            return await client.call_required_tool(
                tool_name,
                arguments or {},
            )

        finally:

            await client.close()




    async def list_tools(self,server_name: str,):

        """
        Discover tools exposed by an MCP server.
        """

        config: MCPServerConfig = (self.server_registry.get(server_name))

        client = MCPClient(config=config,credential_provider=self.credential_provider,)

        try:
            await client.connect()

            return await client.list_tools()

        finally:
            await client.close()



    async def discover_server_tools(self,server_name: str,) -> list:
        """
        Discover tools exposed by an MCP server.
        """

        config = self.server_registry.get(server_name)

        client = MCPClient(config=config,credential_provider=self.credential_provider,)

        try:
            await client.connect()

            tools = await client.list_tools()

            self.tool_catalog.register_tools(server_name,tools,)

            return tools

        finally:
            await client.close()





    async def find_tool(
    self,
    server_name: str,
    tool_name: str,
):
        """
        Find a specific tool exposed by an MCP server.
        """

        await self._ensure_tool_discovered(
            server_name=server_name,
            tool_name=tool_name,
        )

        return self.tool_catalog.get_tool(
            server_name,
            tool_name,
        )




    async def execute_session(
        self,
        server_name: str,
        calls: list[tuple[str, dict]],
    ) -> list:
        """
        Execute multiple tool calls within a single MCP client session.

        This is required for stateful tool sequences — e.g. Playwright's
        browser_navigate followed by browser_snapshot.  Each call to
        execute() spawns a fresh subprocess (for stdio transport), so
        browser state is lost between calls.  execute_session() keeps one
        connection open for the entire sequence, preserving browser state.

        Returns a list of raw tool results in call order.
        Raises on the first tool error.
        """

        # Ensure all tools are in the catalog before connecting.
        # This may spawn the server once for discovery, but the session
        # below is a separate, persistent connection used for the actual calls.
        for tool_name, _ in calls:
            await self._ensure_tool_discovered(
                server_name=server_name,
                tool_name=tool_name,
            )

        # Validate all tools against guardrails before touching the server.
        for tool_name, _ in calls:
            self.guardrail.validate(
                server_name=server_name,
                tool_name=tool_name,
            )

        config = self.server_registry.get(server_name)
        client = MCPClient(
            config=config,
            credential_provider=self.credential_provider,
        )

        try:
            await client.connect()
            results = []
            for tool_name, arguments in calls:
                result = await client.call_tool(tool_name, arguments or {})
                results.append(result)
            return results
        finally:
            await client.close()

    async def _ensure_tool_discovered(
        self,
        server_name: str,
        tool_name: str,
    ) -> None:
        """
        Ensure the requested MCP tool exists in the catalog.

        If the server has not been discovered yet, discover its tools.
        If the server is already discovered but the requested tool is
        missing, discovery is refreshed.
        """

        if self.tool_catalog.has_tool(
            server_name,
            tool_name,
        ):
            return

        await self.discover_server_tools(
            server_name
        )

        if not self.tool_catalog.has_tool(
            server_name,
            tool_name,
        ):
            raise RuntimeError(
                f"MCP tool '{tool_name}' was not found "
                f"on server '{server_name}'."
            )