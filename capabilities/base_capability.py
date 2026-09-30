from abc import ABC, abstractmethod
from typing import Any


class BaseCapability(ABC):
    """
    Base contract for all capabilities.

    A capability represents an executable business capability
    that can be resolved and invoked by the workflow.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique capability name."""
        raise NotImplementedError

    

    @abstractmethod
    def execute(self, task: Any, context: Any = None) -> Any:
        """
        Execute the capability.

        Args:
            task: Task assigned to the capability.
            context: Optional execution context.

        Returns:
            Capability-specific result.
        """
        raise NotImplementedError