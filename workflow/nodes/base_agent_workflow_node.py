from models.workflow_state import WorkflowState
from workflow.nodes.base_workflow__node import BaseWorkflowNode


class BaseAgentWorkflowNode(BaseWorkflowNode):

    """
    ==========================================================
    Class : BaseAgentWorkflowNode
    ==========================================================

    Purpose:
        Base class for workflow nodes that simply invoke
        an Agent.

    Responsibilities:
        • Store Agent instance.
        • Execute Agent.
        • Update WorkflowState.

    This class removes duplicated execute()
    implementations across simple workflow nodes.
    ==========================================================
    """

    def __init__(self, agent):

        self.agent = agent


    def execute(self,state: WorkflowState) -> WorkflowState:

        state.update(self.agent.run(state.app_state))
        return state