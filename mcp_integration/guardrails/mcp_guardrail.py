from mcp_integration.catalog.mcp_tool_catalog import MCPToolCatalog
from mcp_integration.guardrails.mcp_tool_policy import MCPToolAccessLevel, MCPToolPolicy


class MCPGuardrail:
    """
    Applies execution policies to MCP tools.

    The guardrail evaluates tool metadata and configured policy.
    It does not execute tools.
    """


    def __init__(self,catalog: MCPToolCatalog,policy: MCPToolPolicy,) -> None:

        self._catalog = catalog
        self._policy = policy



    def validate(self,server_name: str,tool_name: str,):
        """
        Validate whether an MCP tool is permitted to execute.
        """

        if not self._catalog.has_tool(server_name,tool_name,):

            raise PermissionError(f"MCP tool {tool_name} was not discovered on server {server_name}.")

        tool = self._catalog.get_tool(server_name,tool_name,)

        annotations = getattr(tool,"annotations",None,)

        access_level = self._policy.classify(tool_name=tool_name,annotations=annotations,)

        if access_level == MCPToolAccessLevel.DESTRUCTIVE:

            raise PermissionError(f"Destructive MCP tool {tool_name} requires explicit authorization.")

        return access_level