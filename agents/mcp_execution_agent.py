from agents.base_agent import BaseAgent
from utils.logger import logger


class MCPExecutionAgent(BaseAgent):
    """
    Specialist agent responsible for creating an execution plan
    from available MCP tools.

    The agent does not execute MCP tools.
    """

    def __init__(
        self,
        mcp_execution_service,
    ) -> None:

        super().__init__()

        self.mcp_execution_service = (
            mcp_execution_service
        )

    def execute(
        self,
        state,
    ):
        """
        Create an MCP execution plan.

        Expected state:

            {
                "execution_context": ...,
                "available_tools": ...
            }
        """

        plan = (
            self.mcp_execution_service.create_plan(
                execution_context=state[
                    "execution_context"
                ],
                available_tools=state[
                    "available_tools"
                ],
            )
        )

        logger.info(
            "MCP execution plan created: "
            f"{[operation.tool_name for operation in plan.operations]}"
        )

        return plan
