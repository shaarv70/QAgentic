from agents.supervisor_agent import SupervisorAgent
from artifacts.artifact_manager import ArtifactManager
from registries.agent_registry import AgentRegistry
from registries.node_registry import NodeRegistry
from registries.provider_registry import ProviderRegistry
from registries.tool_registry import ToolRegistry
from services.llm_service import LLMService
from workflow.langgraph_engine import LangGraphEngine
from workflow.workflow_builder import WorkflowBuilder
from workflow.workflow_manager import WorkflowManager


class ApplicationContainer:
    """
==========================================================
Class : ApplicationContainer
==========================================================

Purpose:
    Creates and wires together all framework components.

Responsibilities:
    • Instantiate registries.
    • Create workflow infrastructure.
    • Perform dependency injection.
    • Return a fully configured SupervisorAgent.

This class NEVER:
    ❌ Executes workflows.
    ❌ Contains business logic.
    ❌ Calls LLM providers.
    ❌ Executes workflow nodes.

Object Graph:

    ProviderRegistry
            │
            ▼
      ToolRegistry
            │
            ▼
     AgentRegistry
            │
            ▼
      NodeRegistry
            │
            ▼
    WorkflowBuilder
            │
            ▼
    LangGraphEngine
            │
            ▼
    WorkflowManager
            │
            ▼
    SupervisorAgent

==========================================================
"""
    def create_supervisor(self):

        provider_registry = ProviderRegistry()

        llm_service = LLMService(provider_registry)

        tool_registry = ToolRegistry(llm_service)

        agent_registry = AgentRegistry(
            tool_registry,
            llm_service
        )

        artifact_manager = ArtifactManager()

        node_registry = NodeRegistry(
            agent_registry,
            artifact_manager
        )

        workflow_builder = WorkflowBuilder(
            node_registry
        )

        workflow_engine = LangGraphEngine(
            workflow_builder
        )

        workflow_manager = WorkflowManager(
            workflow_engine
        )

        return SupervisorAgent(
            workflow_manager
        )