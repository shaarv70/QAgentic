from models.workflow_state import WorkflowState
from workflow.workflow_engine import WorkflowEngine


class LangGraphEngine(WorkflowEngine):

    """
    ==========================================================
    Class : LangGraphEngine
    ==========================================================

    Purpose:
        Executes the compiled LangGraph workflow.

    Responsibilities:
        • Compile workflow once.
        • Execute workflow.
        • Return updated WorkflowState.

    This class NEVER:

        ❌ Creates workflow nodes.
        ❌ Connects workflow nodes.
        ❌ Calls agents directly.

    Created By:
        WorkflowManager

    Depends On:
        WorkflowBuilder
    """

    def __init__(self,workflow_builder):

        """
        Compile the workflow only once.

        Every execution reuses the compiled
        workflow instance.
        """

        self.compiled_graph = workflow_builder.build()





    def execute(self,workflow_state: WorkflowState) -> WorkflowState:

        """
        Executes the complete workflow.

        LangGraph Runtime automatically
        invokes every node based on the
        configured graph.
        """
        result = self.compiled_graph.invoke(workflow_state)

        # LangGraph returns the workflow state as a dictionary.
        # Reconstruct the WorkflowState wrapper so the rest of the
        # framework remains independent of LangGraph's internal
        # representation.
        if isinstance(result, dict):

            app_state = result.get("app_state")

            if app_state is None:
                raise RuntimeError(
            "LangGraph returned a state without 'app_state'.")

            return WorkflowState(app_state=app_state)


        return result
