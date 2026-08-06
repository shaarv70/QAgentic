from typing import cast
from registries.base_registry import BaseRegistry
from services.artifact_publish_service import ArtifactPublisher
from workflow.nodes.base_workflow__node import BaseWorkflowNode
from workflow.nodes.publish_node import PublishNode
from workflow.nodes.requirement_node import RequirementNode
from workflow.nodes.requirement_intelligence_node import RequirementIntelligenceNode
from workflow.nodes.planner_node import PlannerNode
from workflow.nodes.execution_workflow_node import ExecutionWorkflowNode
from workflow.constants import (
    REQUIREMENT,
    INTELLIGENCE,
    PLANNER,
    EXECUTION,PUBLISH
)




class NodeRegistry(BaseRegistry):

    """
    ==========================================================
    Class : NodeRegistry
    ==========================================================

    Purpose:
        Creates and stores every workflow node.

    Responsibilities:

• Create workflow nodes.
• Store workflow nodes.
• Return workflow nodes.
• Register workflow nodes with LangGraph.

This class NEVER:

❌ Executes nodes.
❌ Connects workflow nodes.
❌ Builds the workflow.
❌ Executes LangGraph.

    WorkflowBuilder is responsible for
    connecting the registered nodes.
    """

    def __init__(self,agent_registry,artifact_manager):

        super().__init__()

        self.agent_registry = agent_registry

        self.artifact_manager = artifact_manager

        self._register_default_nodes()





    def _register_default_nodes(self):

        publish_service = ArtifactPublisher(self.artifact_manager)



        self.register(
            REQUIREMENT,
            RequirementNode(self.agent_registry)
        )

        self.register(
            INTELLIGENCE,
            RequirementIntelligenceNode(self.agent_registry)
        )

        self.register(
            PLANNER,
            PlannerNode(self.agent_registry)
        )

        self.register(
            EXECUTION,
            ExecutionWorkflowNode(self.agent_registry)
        )

        self.register(
            PUBLISH,
            PublishNode(publish_service))




    def register_all(self,workflow_graph) -> None:
        """
    ==========================================================
    Register every workflow node with the LangGraph instance.

    WorkflowBuilder delegates node registration to the
    NodeRegistry so it does not know individual workflow nodes.
    ==========================================================
    """

        for node_name, node in self.items():

            workflow_node = cast(BaseWorkflowNode,node)

            workflow_graph.add_node(node_name,workflow_node.execute)