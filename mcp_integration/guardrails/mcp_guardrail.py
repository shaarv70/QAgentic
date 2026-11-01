from mcp_integration.catalog.mcp_tool_catalog import MCPToolCatalog
from mcp_integration.guardrails.mcp_tool_policy import MCPToolAccessLevel, MCPToolPolicy


class MCPGuardrail:
    """
    Applies execution policies to MCP tools.

    The guardrail evaluates tool metadata and configured policy.
    It does not execute tools.
    """

    def __init__(self, catalog: MCPToolCatalog, policy: MCPToolPolicy) -> None:
        self._catalog = catalog
        self._policy = policy

    def validate(self, server_name: str, tool_name: str) -> MCPToolAccessLevel:
        """
        Validate whether an MCP tool is permitted to execute.

        Raises PermissionError if the tool is classified as DESTRUCTIVE
        and has not been explicitly authorized via a server override.
        """

        if not self._catalog.has_tool(server_name, tool_name):
            raise PermissionError(
                f"MCP tool {tool_name} was not discovered on server {server_name}."
            )

        tool = self._catalog.get_tool(server_name, tool_name)
        annotations = getattr(tool, "annotations", None)

        # Pass server_name so server-specific overrides take precedence
        # over annotation hints (e.g. Playwright sets destructive_hint=True
        # on browser_navigate, which is safe in QAgentic's inspection context).
        access_level = self._policy.classify(
            tool_name=tool_name,
            annotations=annotations,
            server_name=server_name,
        )

        if access_level == MCPToolAccessLevel.DESTRUCTIVE:
            raise PermissionError(
                f"Destructive MCP tool {tool_name} requires explicit authorization."
            )

        return access_level
