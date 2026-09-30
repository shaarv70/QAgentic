from capabilities.test_execution.models import TestExecutionRequest
from domain.execution.execution_intent import ExecutionIntent

class ExecutionRequestBuilder:
    """
    Converts a normalized ExecutionIntent into a
    TestExecutionRequest.

    ```
    This class does NOT:
        - interpret natural language
        - read repositories
        - resolve repositories
        - resolve execution servers
        - execute tests

    It only maps structured intent into the execution request
    consumed by TestExecutionCapability.
    """

def build(
    self,
    intent: ExecutionIntent,
) -> TestExecutionRequest:

    if not intent.instruction:
        raise ValueError(
            "Execution instruction cannot be empty."
        )

    return TestExecutionRequest(
        repository_path=intent.repository_path,
        repository_url=intent.repository_url,
        branch=intent.branch,
        framework=intent.framework,
        mcp_server=intent.mcp_server,
        command=intent.command,
        tool_name=intent.tool_name,
        tool_arguments=intent.tool_arguments,
        test_path=intent.test_path,
    )

