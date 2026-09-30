from models.workflow_state import WorkflowState


class WorkflowManager:

    """
    ==========================================================
    Class : WorkflowManager
    ==========================================================

    Purpose:
        Entry point for the complete workflow layer.

    The manager remains deliberately thin.

    It does NOT:
        • create checkpoints
        • handle approvals
        • interact with LangGraph directly
        • execute business logic

    It simply delegates execution/resume to WorkflowEngine.
    ==========================================================
    """

    def __init__(self, workflow_engine):

        self.workflow_engine = workflow_engine

    def execute(
        self,
        workflow_state: WorkflowState,
        resume=None,
    ) -> WorkflowState:

        return self.workflow_engine.execute(
            workflow_state,
            resume=resume,
        )