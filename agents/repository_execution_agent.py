from typing import Any

from domain.repository.repository_execution_plan import (
    RepositoryExecutionPlan,
)


class RepositoryExecutionAgent:
    """
    Specialist agent responsible for repository execution planning.

    The agent itself does not communicate with MCP directly.

    Flow:

        RepositoryCapability
                ↓
        MCPRepositoryProvider
                ↓
        RepositoryExecutionAgent
                ↓
        RepositoryExecutionService
                ↓
               LLM
                ↓
        RepositoryExecutionPlan
    """

    def __init__(
        self,
        repository_execution_service,
    ) -> None:

        self.repository_execution_service = (
            repository_execution_service
        )

    def execute(
        self,
        context: dict[str, Any],
    ) -> RepositoryExecutionPlan:
        """
        Create a repository execution plan.

        Expected context:

            {
                "repository_operation": RepositoryOperation,
                "repository_context": {...},
                "available_tools": [...]
            }
        """

        repository_operation = context.get(
            "repository_operation"
        )

        if repository_operation is None:
            raise ValueError(
                "RepositoryExecutionAgent requires "
                "'repository_operation'."
            )

        repository_context = context.get(
            "repository_context"
        )

        if not isinstance(
            repository_context,
            dict,
        ):
            raise ValueError(
                "RepositoryExecutionAgent requires "
                "'repository_context' as a dictionary."
            )

        available_tools = context.get(
            "available_tools"
        )

        if not isinstance(
            available_tools,
            list,
        ):
            raise ValueError(
                "RepositoryExecutionAgent requires "
                "'available_tools' as a list."
            )

        return self.repository_execution_service.create_plan(
            repository_operation=repository_operation,
            repository_context=repository_context,
            available_tools=available_tools,
        )