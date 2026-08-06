from abc import ABC, abstractmethod

from models.workflow_state import WorkflowState


class WorkflowEngine(ABC):
    """
    ==========================================================
    Base contract for all workflow engines.
    ==========================================================
    """

    @abstractmethod
    def execute(self,workflow_state: WorkflowState) -> WorkflowState:
        """
        Execute the workflow and return the updated state.
        """
        pass