from abc import ABC, abstractmethod

from models.workflow_state import WorkflowState


class WorkflowEngine(ABC):
    """
    ==========================================================
    Base contract for all workflow engines.
    ==========================================================
    """

    @abstractmethod
    def execute(
    self,
    workflow_state: WorkflowState,
    resume=None,
) -> WorkflowState:
        """
        Execute or resume the workflow.

        resume=None starts a new workflow.

        A non-None resume value resumes an interrupted
        LangGraph workflow.
        """
    pass