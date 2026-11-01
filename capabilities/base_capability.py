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

    @property
    def review_required(self) -> bool:
        """
        Whether the workflow should run a quality review on this
        capability's output.  Override with False for best-effort
        capabilities (e.g. page_inspection) whose graceful-degradation
        path produces an intentionally empty artifact that must not
        block the pipeline.
        """
        return True

    @property
    def healable(self) -> bool:
        """
        Whether this capability supports self-healing correction via correct().

        When True, execute_task() returns a FAILED artifact instead of raising
        so that the review + correction cycle can trigger self-healing.
        Override with True in capabilities that implement correct().
        """
        return False

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