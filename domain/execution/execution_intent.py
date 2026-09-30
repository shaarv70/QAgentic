from dataclasses import dataclass
from enum import Enum
from typing import Any

class ExecutionInputType(str, Enum):
    COMMAND = "command"
    REQUIREMENT = "requirement"
    DOCUMENT = "document"




@dataclass(frozen=True)
class ExecutionIntent:
    """
    Normalized intent produced from user input.

    ```
    This is deliberately independent of:
        - Selenium
        - Playwright
        - Appium
        - GitHub
        - any specific test framework

    MCP is represented only as execution routing information.
    """

    input_type: ExecutionInputType
    instruction: str

    repository_path: str | None = None
    repository_url: str | None = None
    branch: str | None = None

    framework: str | None = None

    # Explicit execution-server selection.
    mcp_server: str | None = None

    command: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None

    test_path: str | None = None

    document_path: str | None = None

    metadata: dict[str, Any] | None = None
