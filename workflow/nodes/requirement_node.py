from services.run_service import RunService
from workflow.nodes.base_workflow__node import BaseWorkflowNode
from models.workflow_state import WorkflowState


class RequirementNode(BaseWorkflowNode):
    """
    =====================================================
    Class : RequirementNode
    =====================================================

    Purpose:
        Initializes every workflow execution.

    Responsibilities:
        • Generate Run Id.
        • Execute RequirementAgent.

    Called By:
        LangGraph Runtime
    =====================================================
    """


    def __init__(self, agent_registry):

        self.requirement_agent = agent_registry.get("requirement")



    def execute(self, state: WorkflowState) -> WorkflowState:

        app_state = state.app_state
        app_state.run_id =RunService.create_run_id()
        state.update(self.requirement_agent.run(app_state))

        return state