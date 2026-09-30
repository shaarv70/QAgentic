from enum import Enum


class MCPToolAccessLevel(str, Enum):
    
    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"
    UNKNOWN = "unknown"


class MCPToolPolicy:
    """
    Determines the QAgentic access classification for an MCP tool.

    MCP annotations are used when available. QAgentic policy is
    responsible for additional classification when MCP metadata
    is insufficient.
    """

    def classify(self,tool_name: str,annotations: object | None,) -> MCPToolAccessLevel:

        if annotations is not None:

            destructive = getattr(annotations,"destructive_hint",None,)

            if destructive is True:

                return MCPToolAccessLevel.DESTRUCTIVE

        return self._classify_by_name(tool_name)



    def _classify_by_name(self,tool_name: str,) -> MCPToolAccessLevel:

        name = tool_name.lower()

        destructive_keywords = (
            "delete",
            "remove",
            "destroy",
            "terminate",
            "revoke",
        )

        write_keywords = (
            "create",
            "update",
            "write",
            "push",
            "merge",
            "fork",
            "add",
            "edit",
            "modify",
            "request",
            "run",
        )

        if any(keyword in name for keyword in destructive_keywords):

            return MCPToolAccessLevel.DESTRUCTIVE

        if any(keyword in name for keyword in write_keywords):

            return MCPToolAccessLevel.WRITE

        return MCPToolAccessLevel.READ