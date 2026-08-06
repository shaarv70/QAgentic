from models.workflow_state import WorkflowState


class WorkflowManager:

    """
    ==========================================================
    Class : WorkflowManager
    ==========================================================

    Purpose:
        Entry point for the complete workflow layer.

    Responsibilities:
        • Accept workflow execution requests.
        • Delegate execution to LangGraphEngine.
        • Return the updated WorkflowState.

    This class NEVER:

        ❌ Creates workflow nodes.
        ❌ Creates graphs.
        ❌ Calls agents.
        ❌ Executes business logic.

    Created By:
        app.py

    Used By:
        SupervisorAgent
    """

    def __init__(self,workflow_engine):

        self.workflow_engine = workflow_engine



    def execute(self,workflow_state: WorkflowState) -> WorkflowState:
        """
        Starts workflow execution.

        Supervisor should always invoke
        the workflow through this method.
        """

        return self.workflow_engine.execute(workflow_state)