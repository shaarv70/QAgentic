from workflow.nodes.base_workflow__node import BaseWorkflowNode
from models.workflow_state import WorkflowState


class PublishNode(BaseWorkflowNode):

    """
    ==========================================================
    Class : PublishNode
    ==========================================================

    Purpose:
        Final workflow node.

    Responsibilities:
        • Publish generated artifacts.
        • Save artifacts.
        • Notify downstream systems (future).

    Current Status:
        Placeholder implementation.

    This node will replace artifact publishing
    currently present in Supervisor.
    ==========================================================
    """

    def __init__(self,publish_service):

        self.publish_service = publish_service



    def execute(self,state: WorkflowState)->WorkflowState:

        app_state = state.app_state
        self.publish_service.publish(app_state)

        return state

