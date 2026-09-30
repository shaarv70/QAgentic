from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(slots=True)
class TestExecutionRequest:
    """
    Represents a request to execute a test suite.

    The request is intentionally framework-agnostic.
    """

    repository_path: Optional[str] = None
    repository_url: Optional[str] = None
    branch: Optional[str] = None

    framework: Optional[str] = None
    mcp_server: Optional[str] = None
    command: Optional[str] = None
    tool_name: Optional[str] = None
    tool_arguments: Optional[dict[str, Any]] = None
    test_path: Optional[str] = None


@dataclass(slots=True)
class TestExecutionResult:
    """
    Represents the result of a test execution.
    """

    success: bool
    exit_code: int
    command: str

    stdout: str = ""
    stderr: str = ""

    duration_seconds: float = 0.0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )