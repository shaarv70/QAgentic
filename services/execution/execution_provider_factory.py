from domain.execution.execution_policy import ExecutionPolicy
from infrastructure.execution.mcp.mcp_execution_provider import MCPExecutionProvider
from domain.execution.execution_server_config import  ExecutionServerConfig
from mcp_integration.tool.mcp_tool_executor import MCPToolExecutor
from capabilities.test_execution.ports.execution_provider import ExecutionProvider
from infrastructure.execution.local.local_execution_provider import LocalExecutionProvider


class ExecutionProviderFactory:
    """
    Creates the correct execution provider for an execution server.
    """

    def __init__(
        self,
        mcp_tool_executor: MCPToolExecutor,
        execution_policy: ExecutionPolicy | None = None,
    ) -> None:

        self.mcp_tool_executor = mcp_tool_executor

        self.execution_policy = (
            execution_policy
            if execution_policy is not None
            else ExecutionPolicy()
        )

    def create(
        self,
        config: ExecutionServerConfig,
    ) -> ExecutionProvider:

        if config.provider_type == "mcp":

            if not config.server_name:
                raise ValueError(
                    f"Execution server '{config.name}' "
                    "does not define an MCP server name."
                )

            return MCPExecutionProvider(
                mcp_tool_executor=self.mcp_tool_executor,
                server_name=config.server_name,
                policy=self.execution_policy,
            )

        if config.provider_type == "local":

            return LocalExecutionProvider(
                policy=self.execution_policy,
            )

        raise ValueError(
            f"Unsupported execution provider type: "
            f"{config.provider_type}"
        )