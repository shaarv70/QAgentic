from typing import Any


class MCPToolCatalog:
    """
    In-memory catalog of tools exposed by registered MCP servers.

    The catalog stores tool definitions discovered from MCP servers.
    It does not establish connections or execute tools.
    """

    def __init__(self) -> None:

        self._tools: dict[str, dict[str, Any]] = {}



    def register_tools(self,server_name: str,tools: list[Any],) -> None:
        """
        Register or replace the discovered tools for a server.
        """

        self._tools[server_name] = {tool.name: tool for tool in tools}




    def get_tool(self,server_name: str,tool_name: str,) -> Any:
        """
        Return a specific discovered tool.
        """

        server_tools = self._tools.get(server_name)

        if server_tools is None:

            raise KeyError(
                f"No tools discovered for MCP server "
                f"'{server_name}'.")

        try:

            return server_tools[tool_name]

        except KeyError as exc:
            raise KeyError(
                f"MCP tool '{tool_name}' was not found on server '{server_name}'.") from exc




    def has_tool(self,server_name: str,tool_name: str,) -> bool:
        """
        Check whether a server exposes a discovered tool.
        """

        return (
            server_name in self._tools
            and tool_name in self._tools[server_name]
        )




    def get_server_tools(self,server_name: str,) -> list[Any]:
        """
        Return all discovered tools for a server.
        """

        return list(self._tools.get(server_name, {}).values())



    def get_servers(self) -> list[str]:
        """
        Return names of servers with discovered tools.
        """

        return list(self._tools.keys())




    def clear_server(self,server_name: str,) -> None:
        """
        Remove the cached tools for a server.
        """

        self._tools.pop(server_name, None)




    def clear(self) -> None:
        """
        Remove the entire catalog.
        """

        self._tools.clear()



    def is_read_only(self,server_name: str,tool_name: str,) -> bool:

        tool = self.get_tool(server_name, tool_name)

        annotations = getattr(tool, "annotations", None)

        return bool(
            annotations
            and annotations.read_only_hint is True
        )



    def is_destructive(self,server_name: str,tool_name: str,) -> bool:


        tool = self.get_tool(server_name, tool_name)

        annotations = getattr(tool, "annotations", None)

        return bool(
            annotations
            and annotations.destructive_hint is True
        )



    def is_idempotent(self,server_name: str,tool_name: str,) -> bool:

            tool = self.get_tool(server_name, tool_name)

            annotations = getattr(tool, "annotations", None)

            return bool(
                annotations
                and annotations.idempotent_hint is True
            )



    def describe_tool(self,server_name: str,tool_name: str,) -> dict:

            tool = self.get_tool(server_name,tool_name,)

            annotations = getattr(tool,"annotations",None,)

            return {
                "server": server_name,
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "read_only": (
                    annotations.read_only_hint
                    if annotations
                    else None
                ),
                "destructive": (
                    annotations.destructive_hint
                    if annotations
                    else None
                ),
                "idempotent": (
                    annotations.idempotent_hint
                    if annotations
                    else None
                ),
                "open_world": (
                    annotations.open_world_hint
                    if annotations
                    else None
                ),
            }