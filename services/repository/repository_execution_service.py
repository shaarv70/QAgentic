from typing import Any

from ai.builders.prompt_builder import PromptBuilder
from ai.models.llm_request import LLMRequest
from ai.services.ai_service import AIService
from constants.agent_names import AgentNames
from domain.repository.repository_execution_plan import (
    RepositoryExecutionOperation,
    RepositoryExecutionPlan,
)
from domain.repository.repository_operation import (
    RepositoryOperationType,
)


class RepositoryExecutionService:
    """
    Creates an executable repository plan from an LLM response.

    Responsibilities:
        1. Build the repository execution prompt.
        2. Call the configured LLM through AIService.
        3. Parse the JSON response.
        4. Validate the returned plan structure.
        5. Convert the response into domain objects.

    This service does NOT:
        - execute repository tools
        - perform approvals
        - know GitHub/GitLab/Bitbucket details
        - contain MCP transport logic

    It is therefore reusable regardless of the repository provider.
    """

    def __init__(
        self,
        ai_service: AIService,
        prompt_builder: PromptBuilder,
    ) -> None:

        self.ai_service = ai_service
        self.prompt_builder = prompt_builder

    def create_plan(
        self,
        repository_operation,
        repository_context: dict[str, Any],
        available_tools: list[Any],
    ) -> RepositoryExecutionPlan:
        """
        Ask the Repository Execution Agent to translate one semantic
        repository operation into concrete MCP tool operations.

        The semantic repository operation is supplied by QAgentic,
        not invented by the LLM.
        """

        # ----------------------------------------------------------
        # Build the LLM prompt using the existing PromptBuilder.
        # ----------------------------------------------------------
        prompt = self.prompt_builder.repository_execution(
            repository_context=repository_context,
            available_tools=available_tools,
        )

        request = LLMRequest(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
        )

        # ----------------------------------------------------------
        # Use the existing AIService contract.
        #
        # AIService already handles:
        #   - provider selection
        #   - agent profile
        #   - token accounting
        #   - pricing
        #   - retry handling
        # ----------------------------------------------------------
        response = self.ai_service.generate_json(
            AgentNames.REPOSITORY_EXECUTION,
            request,
        )

        return self._parse_plan(
            response=response,
            repository_operation=repository_operation,
        )

    def _parse_plan(
        self,
        response: dict[str, Any],
        repository_operation,
    ) -> RepositoryExecutionPlan:
        """
        Convert the LLM JSON response into a trusted domain plan.

        Important:
            The LLM does NOT decide whether an operation requires
            approval. That decision remains in the domain model.
        """

        if not isinstance(response, dict):
            raise ValueError(
                "Repository execution response must be a JSON object."
            )

        executable = response.get(
            "executable",
            True,
        )

        if not isinstance(executable, bool):
            raise ValueError(
                "'executable' must be a boolean."
            )

        reason = response.get("reason")

        if reason is not None and not isinstance(reason, str):
            raise ValueError(
                "'reason' must be a string when provided."
            )

        operations_data = response.get(
            "operations",
            [],
        )

        if not isinstance(
            operations_data,
            list,
        ):
            raise ValueError(
                "Repository execution response must contain "
                "an 'operations' list."
            )

        operations: list[
            RepositoryExecutionOperation
        ] = []

        for operation_data in operations_data:

            if not isinstance(
                operation_data,
                dict,
            ):
                raise ValueError(
                    "Each repository execution operation "
                    "must be an object."
                )

            tool_name = operation_data.get(
                "tool_name"
            )

            if (
                not isinstance(tool_name, str)
                or not tool_name.strip()
            ):
                raise ValueError(
                    "Repository execution operation "
                    "requires a tool_name."
                )

            arguments = operation_data.get(
                "arguments",
                {},
            )

            if not isinstance(
                arguments,
                dict,
            ):
                raise ValueError(
                    f"Arguments for repository tool "
                    f"'{tool_name}' must be an object."
                )

            depends_on = operation_data.get(
                "depends_on",
                [],
            )

            if not isinstance(
                depends_on,
                list,
            ):
                raise ValueError(
                    f"depends_on for repository tool "
                    f"'{tool_name}' must be a list."
                )

            # ------------------------------------------------------
            # The operation type is NOT trusted from the LLM.
            #
            # The current semantic operation came from QAgentic
            # before the LLM was called.
            #
            # Therefore every generated tool operation belongs to
            # that semantic operation.
            # ------------------------------------------------------
            operations.append(
                RepositoryExecutionOperation(
                    operation=repository_operation.operation,
                    tool_name=tool_name,
                    arguments=arguments,
                    depends_on=depends_on,
                )
            )

        # ----------------------------------------------------------
        # Validate the important semantic invariant:
        #
        # An executable plan must contain at least one operation.
        # ----------------------------------------------------------
        if executable and not operations:
            raise ValueError(
                "Repository execution plan is executable "
                "but contains no operations."
            )

        # ----------------------------------------------------------
        # requires_approval is intentionally NOT read from the LLM.
        #
        # RepositoryExecutionOperation.requires_approval derives
        # from the trusted RepositoryOperationType.
        # ----------------------------------------------------------
        requires_approval = any(
            operation.requires_approval
            for operation in operations
        )

        return RepositoryExecutionPlan(
            plan_id=self._generate_plan_id(),
            executable=executable,
            reason=reason,
            requires_approval=requires_approval,
            operations=operations,
        )

    @staticmethod
    def _generate_plan_id() -> str:
        """
        Generate a unique identifier for the execution plan.
        """

        from uuid import uuid4

        return str(uuid4())