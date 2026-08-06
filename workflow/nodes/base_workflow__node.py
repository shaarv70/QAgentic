from abc import ABC, abstractmethod
from models.workflow_state import WorkflowState


class BaseWorkflowNode(ABC):
    """
    Base contract for every workflow node.
    """

    @abstractmethod
    def execute(self, state: WorkflowState) -> WorkflowState:
        """
        Execute node logic and return the updated workflow state.
        """
        pass