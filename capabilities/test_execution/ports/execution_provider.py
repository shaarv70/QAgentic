from abc import ABC, abstractmethod
from typing import Any


class ExecutionProvider(ABC):
    """
    Contract for execution providers.

    Providers perform the actual execution.

    Examples:
        - MCPExecutionProvider
        - LocalExecutionProvider
        - future remote execution providers
    """

    @abstractmethod
    async def execute(
        self,
        command: str,
        working_directory: str,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute through the underlying execution mechanism.
        """
        raise NotImplementedError