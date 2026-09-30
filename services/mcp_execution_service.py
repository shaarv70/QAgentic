from typing import Any

from ai.builders.prompt_builder import PromptBuilder
from ai.models.llm_request import LLMRequest
from ai.services.ai_service import AIService
from constants.agent_names import AgentNames
from models.mcp_execution_model import (
    MCPExecutionOperation,
    MCPExecutionPlan,
)


class MCPExecutionService:

    def __init__(
        self,
        ai_service: AIService,
        prompt_builder: PromptBuilder,
    ) -> None:

        self.ai_service = ai_service
        self.prompt_builder = prompt_builder

    def create_plan(
        self,
        execution_context: dict[str, Any],
        available_tools: list[Any],
    ) -> MCPExecutionPlan:

        prompt = self.prompt_builder.mcp_execution(
            execution_context=execution_context,
            available_tools=available_tools,
        )

        request = LLMRequest(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
        )

        response = self.ai_service.generate_json(
            AgentNames.MCP_EXECUTION,
            request,
        )

        return self._parse_plan(response)

    def _parse_plan(
        self,
        response: dict[str, Any],
    ) -> MCPExecutionPlan:

        if not isinstance(response, dict):
            raise ValueError(
                "MCP execution response must be an object."
            )

        # ----------------------------------------------------------
        # 1. Parse execution feasibility
        # ----------------------------------------------------------

        executable = response.get(
            "executable",
            True,
        )

        if not isinstance(executable, bool):
            raise ValueError(
                "MCP execution response field "
                "'executable' must be a boolean."
            )

        reason = response.get("reason")

        if reason is not None and not isinstance(
            reason,
            str,
        ):
            raise ValueError(
                "MCP execution response field "
                "'reason' must be a string or null."
            )

        # ----------------------------------------------------------
        # 2. Parse operations
        # ----------------------------------------------------------

        operations_data = response.get(
            "operations",
            [],
        )

        if not isinstance(
            operations_data,
            list,
        ):
            raise ValueError(
                "MCP execution response must contain "
                "an 'operations' list."
            )

        operations = []

        for operation in operations_data:

            if not isinstance(
                operation,
                dict,
            ):
                raise ValueError(
                    "Each MCP operation must be an object."
                )

            tool_name = operation.get(
                "tool_name"
            )

            if not isinstance(
                tool_name,
                str,
            ) or not tool_name.strip():

                raise ValueError(
                    "MCP operation requires a tool_name."
                )

            arguments = operation.get(
                "arguments",
                {},
            )

            if not isinstance(
                arguments,
                dict,
            ):
                raise ValueError(
                    f"Arguments for '{tool_name}' "
                    "must be an object."
                )

            depends_on = operation.get(
                "depends_on",
                [],
            )

            if not isinstance(
                depends_on,
                list,
            ):
                raise ValueError(
                    f"depends_on for '{tool_name}' "
                    "must be a list."
                )

            operations.append(
                MCPExecutionOperation(
                    tool_name=tool_name,
                    arguments=arguments,
                    depends_on=depends_on,
                )
            )

        # ----------------------------------------------------------
        # 3. Validate feasibility contract
        # ----------------------------------------------------------

        if not executable and operations:
            raise ValueError(
                "An MCP execution plan cannot contain "
                "operations when executable is false."
            )

        if executable and not operations:
            raise ValueError(
                "An executable MCP execution plan must "
                "contain at least one operation."
            )

        if not executable and not reason:
            raise ValueError(
                "A non-executable MCP execution plan must "
                "provide a reason."
            )

        return MCPExecutionPlan(
            executable=executable,
            reason=reason,
            operations=operations,
        )