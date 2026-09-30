from abc import ABC, abstractmethod
from typing import Any

from domain.repository.repository_operation import RepositoryOperationType


class RepositoryProvider(ABC):

    @abstractmethod
    async def execute(
        self,
        operation: Any,
        repository: dict[str, Any],
        workflow_state: Any = None,
    ) -> Any:
        raise NotImplementedError