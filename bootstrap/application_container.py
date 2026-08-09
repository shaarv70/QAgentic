from agents.supervisor_agent import SupervisorAgent
from ai.builders.context_builder import ContextBuilder
from ai.builders.prompt_builder import PromptBuilder
from ai.services.pricing_service import PricingService
from ai.token.token_manager import TokenManager
from artifacts.artifact_manager import ArtifactManager
from registries.agent_profile_registry import AgentProfileRegistry
from registries.agent_registry import AgentRegistry
from registries.node_registry import NodeRegistry
from registries.provider_registry import ProviderRegistry
from registries.tool_registry import ToolRegistry
from ai.services.ai_service import AIService
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

        profile_registry = AgentProfileRegistry()

        pricing_service = PricingService()

        context_builder = ContextBuilder()

        prompt_builder = PromptBuilder(context_builder)

        token_manager = TokenManager()

        ai_service = AIService(provider_registry,profile_registry,token_manager,pricing_service)

        tool_registry = ToolRegistry(ai_service,prompt_builder)

        agent_registry = AgentRegistry(tool_registry,ai_service,prompt_builder)

        artifact_manager = ArtifactManager()

        node_registry = NodeRegistry(agent_registry,artifact_manager)

        workflow_builder = WorkflowBuilder(node_registry)

        workflow_engine = LangGraphEngine(workflow_builder)

        workflow_manager = WorkflowManager(workflow_engine)

        return SupervisorAgent(workflow_manager)