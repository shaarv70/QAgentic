from domain.execution.execution_intent import (
    ExecutionInputType,
    ExecutionIntent,
)
from domain.execution.requirement import TestRequirement


class RequirementInterpreter:
    """
    Converts a structured test requirement into an
    ExecutionIntent.

    Natural-language reasoning will be added later.
    """

    def interpret(
        self,
        requirement: TestRequirement,
    ) -> ExecutionIntent:

        if not requirement.description.strip():
            raise ValueError(
                "Requirement description cannot be empty."
            )

        if not requirement.framework:
            raise ValueError(
                "Requirement framework cannot be empty."
            )

        return ExecutionIntent(
            input_type=ExecutionInputType.REQUIREMENT,
            instruction=requirement.description,
            repository_path=requirement.repository_path,
            repository_url=requirement.repository_url,
            branch=requirement.branch,
            framework=requirement.framework,
            test_path=requirement.test_path,
        )