from agents.supervisor_agent import SupervisorAgent
from ai.builders.context_builder import ContextBuilder
from ai.builders.prompt_builder import PromptBuilder
from ai.services.pricing_service import PricingService
from ai.token.token_manager import TokenManager
from artifacts.artifact_manager import ArtifactManager
from memory.embeddings.ollama_embedding_provider import OllamaEmbeddingProvider
from memory.embeddings.sentence_transformer_embedding_provider import SentenceTransformerEmbeddingProvider
from memory.episodic.episode_service import EpisodeService
from memory.memory_context_service import MemoryContextService
from memory.memory_manager import MemoryManager
from memory.procedural.default_procedures import get_default_procedures
from memory.procedural.procedural_memory import ProceduralMemory
from memory.memory_retriever import MemoryRetriever
from memory.stores.sqlite_memory_store import SQLiteMemoryStore
from memory.memory_policy import MemoryPolicy
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

        memory_store = SQLiteMemoryStore("memory.db")

        memory_policy = MemoryPolicy(minimum_confidence=0.7)

        embedding_provider = SentenceTransformerEmbeddingProvider(model="all-MiniLM-L6-v2")

        memory_retriever = MemoryRetriever(store=memory_store,embedding_provider=embedding_provider,)

        memory_manager = MemoryManager(store=memory_store,policy=memory_policy,retriever=memory_retriever,)

        episode_service = EpisodeService(memory_manager=memory_manager)

        procedural_memory = ProceduralMemory(memory_manager=memory_manager)

        procedural_memory.seed_many(get_default_procedures())

        context_builder = ContextBuilder(memory_manager=memory_manager)

        memory_context_service = MemoryContextService(context_builder=context_builder,)

        prompt_builder = PromptBuilder(context_builder,memory_context_service)

        token_manager = TokenManager()

        ai_service = AIService(provider_registry,profile_registry,token_manager,pricing_service)

        tool_registry = ToolRegistry(ai_service,prompt_builder)

        agent_registry = AgentRegistry(tool_registry,ai_service,prompt_builder,episode_service)

        artifact_manager = ArtifactManager()

        node_registry = NodeRegistry(agent_registry,artifact_manager,episode_service)

        workflow_builder = WorkflowBuilder(node_registry)

        workflow_engine = LangGraphEngine(workflow_builder)

        workflow_manager = WorkflowManager(workflow_engine)

        return SupervisorAgent(workflow_manager , episode_service,)