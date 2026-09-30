from typing import Any

from domain.execution.execution_policy import ExecutionPolicy
from capabilities.test_execution.ports.execution_provider import ExecutionProvider
from mcp_integration.tool.mcp_tool_executor import MCPToolExecutor


class MCPExecutionProvider(ExecutionProvider):
    """
    Execution provider backed by an external MCP server.

    The provider is generic and does not contain logic for any
    specific MCP server, tool, framework, or automation library.

    Server selection comes from ExecutionServerConfig.

    Tool selection comes from execution metadata.
    """

    def __init__(
        self,
        mcp_tool_executor: MCPToolExecutor,
        server_name: str,
        policy: ExecutionPolicy,
    ) -> None:

        self.mcp_tool_executor = mcp_tool_executor
        self.server_name = server_name
        self.policy = policy

    async def execute(
        self,
        command: str | None,
        working_directory: str,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute a single MCP tool operation.

        `command` is retained in the provider interface for
        compatibility with ExecutionProvider.

        MCP execution itself is driven by metadata.
        """

        metadata = metadata or {}

        tool_name = metadata.get(
            "tool_name"
        )

        if not tool_name:
            raise ValueError(
                "MCP execution requires "
                "metadata['tool_name']."
            )

        tool_arguments = metadata.get(
            "tool_arguments"
        )

        if tool_arguments is None:
            arguments: dict[str, Any] = {}

        else:

            if not isinstance(
                tool_arguments,
                dict,
            ):
                raise TypeError(
                    "metadata['tool_arguments'] "
                    "must be a dictionary."
                )

            arguments = dict(
                tool_arguments
            )

        return await self.mcp_tool_executor.execute(
            server_name=self.server_name,
            tool_name=tool_name,
            arguments=arguments,
        )

