from workflow.nodes.base_agent_workflow_node import BaseAgentWorkflowNode
from models.workflow_state import WorkflowState




class RequirementIntelligenceNode(BaseAgentWorkflowNode):
    """
==================================================
Class : RequirementIntelligenceNode
==================================================

Purpose:
    Executes RequirementIntelligenceAgent.

Created By:
    NodeRegistry

Called By:
    LangGraph Runtime

Calls:
    RequirementIntelligenceAgent

Receives:
    WorkflowState

Returns:
    Updated WorkflowState

Stores:
    RequirementIntelligenceAgent

Does NOT Know:
    Planner
    Execution
    Review

Reason:
    Acts as an adapter between LangGraph and our
    existing RequirementIntelligenceAgent.
"""



    def __init__(self, agent_registry):

        self.intelligence_agent = agent_registry.get("intelligence")





    def execute(self,state: WorkflowState) -> WorkflowState:
        app_state = state.app_state
        state.update(self.intelligence_agent.run(app_state))
        return state