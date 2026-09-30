from agents.mcp_execution_agent import MCPExecutionAgent
from agents.repository_analysis_agent import RepositoryAnalysisAgent
from agents.repository_execution_agent import RepositoryExecutionAgent
from agents.supervisor_agent import SupervisorAgent

from ai.builders.context_builder import ContextBuilder
from ai.builders.prompt_builder import PromptBuilder
from ai.services.ai_service import AIService
from ai.services.pricing_service import PricingService
from ai.token.token_manager import TokenManager

from artifacts.artifact_manager import ArtifactManager

from domain.execution.execution_policy import ExecutionPolicy

from infrastructure.repository.git.git_repository_materializer import (
    GitRepositoryMaterializer,
)
from infrastructure.repository.mcp.mcp_repository_provider import (
    MCPRepositoryProvider,
)

from memory.embeddings.sentence_transformer_embedding_provider import (
    SentenceTransformerEmbeddingProvider,
)
from memory.episodic.episode_service import EpisodeService
from memory.memory_context_service import MemoryContextService
from memory.memory_manager import MemoryManager
from memory.memory_policy import MemoryPolicy
from memory.memory_retriever import MemoryRetriever
from memory.procedural.default_procedures import get_default_procedures
from memory.procedural.procedural_memory import ProceduralMemory
from memory.stores.sqlite_memory_store import SQLiteMemoryStore

from mcp_integration.auth.environment_credential_provider import (
    EnvironmentCredentialProvider,
)
from mcp_integration.catalog.mcp_tool_catalog import MCPToolCatalog
from mcp_integration.guardrails.mcp_guardrail import MCPGuardrail
from mcp_integration.guardrails.mcp_tool_policy import MCPToolPolicy
from mcp_integration.tool.mcp_tool_executor import MCPToolExecutor

from registries.agent_profile_registry import AgentProfileRegistry
from registries.agent_registry import AgentRegistry
from registries.capability_registry import CapabilityRegistry
from registries.execution_server_registry import ExecutionServerRegistry
from registries.mcp_server_registry import MCPServerRegistry
from registries.node_registry import NodeRegistry
from registries.provider_registry import ProviderRegistry
from registries.tool_registry import ToolRegistry

from services.action_catalog import ActionCatalog
from services.approval.in_memory_approval_service import (
    InMemoryApprovalService,
)
from services.execution.execution_provider_factory import (
    ExecutionProviderFactory,
)
from services.execution.execution_server_resolver import (
    ExecutionServerResolver,
)
from services.mcp_execution_service import MCPExecutionService

from services.repository.repository_analysis_service import (
    RepositoryAnalysisService,
)
from services.repository.repository_discovery import RepositoryDiscovery
from services.repository.repository_execution_service import (
    RepositoryExecutionService,
)
from services.repository.repository_resolver import RepositoryResolver

from services.workspace.automation_workspace_materializer import (
    AutomationWorkspaceMaterializer,
)
from services.workspace.local_workspace_service import (
    LocalWorkspaceService,
)

from workflow.langgraph_engine import LangGraphEngine
from workflow.workflow_builder import WorkflowBuilder
from workflow.workflow_manager import WorkflowManager


class ApplicationContainer:
    """
    Creates and wires together all framework components.

    The container performs dependency injection only.
    It does not execute workflows or contain business logic.
    """

    mcp_tool_executor: MCPToolExecutor
    mcp_tool_catalog: MCPToolCatalog
    mcp_guardrail: MCPGuardrail
    mcp_tool_policy: MCPToolPolicy
    capability_registry: CapabilityRegistry

    def create_supervisor(self):

        # ==========================================================
        # Core registries / AI
        # ==========================================================

        provider_registry = ProviderRegistry()
        profile_registry = AgentProfileRegistry()

        pricing_service = PricingService()
        token_manager = TokenManager()

        ai_service = AIService(
            provider_registry,
            profile_registry,
            token_manager,
            pricing_service,
        )

        # ==========================================================
        # Memory
        # ==========================================================

        memory_store = SQLiteMemoryStore("memory.db")

        memory_policy = MemoryPolicy(
            minimum_confidence=0.7,
        )

        embedding_provider = SentenceTransformerEmbeddingProvider(
            model="all-MiniLM-L6-v2",
        )

        memory_retriever = MemoryRetriever(
            store=memory_store,
            embedding_provider=embedding_provider,
        )

        memory_manager = MemoryManager(
            store=memory_store,
            policy=memory_policy,
            retriever=memory_retriever,
        )

        episode_service = EpisodeService(
            memory_manager=memory_manager,
        )

        procedural_memory = ProceduralMemory(
            memory_manager=memory_manager,
        )

        procedural_memory.seed_many(
            get_default_procedures()
        )

        context_builder = ContextBuilder(
            memory_manager=memory_manager,
        )

        memory_context_service = MemoryContextService(
            context_builder=context_builder,
        )

        prompt_builder = PromptBuilder(
            context_builder,
            memory_context_service,
        )

        tool_registry = ToolRegistry(
            ai_service,
            prompt_builder,
        )

        # ==========================================================
        # MCP infrastructure
        # ==========================================================

        server_registry = MCPServerRegistry()

        credential_provider = EnvironmentCredentialProvider()

        self.mcp_tool_catalog = MCPToolCatalog()

        self.mcp_tool_policy = MCPToolPolicy()

        self.mcp_guardrail = MCPGuardrail(
            self.mcp_tool_catalog,
            policy=self.mcp_tool_policy,
        )

        self.mcp_tool_executor = MCPToolExecutor(
            server_registry=server_registry,
            credential_provider=credential_provider,
            tool_catalog=self.mcp_tool_catalog,
            guardrail=self.mcp_guardrail,
        )

        # ==========================================================
        # Test execution infrastructure
        # ==========================================================

        execution_server_registry = ExecutionServerRegistry()

        execution_server_resolver = ExecutionServerResolver(
            execution_server_registry
        )

        execution_policy = ExecutionPolicy(
            allowed_commands=frozenset(
                (
                    "python",
                    "mvn",
                )
            ),
            allow_shell=True,
        )

        execution_provider_factory = ExecutionProviderFactory(
            mcp_tool_executor=self.mcp_tool_executor,
            execution_policy=execution_policy,
        )

        mcp_execution_service = MCPExecutionService(
            ai_service=ai_service,
            prompt_builder=prompt_builder,
        )

        mcp_execution_agent = MCPExecutionAgent(
            mcp_execution_service=mcp_execution_service,
        )

        # ==========================================================
        # Repository execution planning
        # ==========================================================

        repository_execution_service = RepositoryExecutionService(
            ai_service=ai_service,
            prompt_builder=prompt_builder,
        )

        repository_execution_agent = RepositoryExecutionAgent(
            repository_execution_service=repository_execution_service,
        )

        # ==========================================================
        # Repository analysis
        #
        # Repository workspace
        #       ↓
        # RepositoryAnalysisAgent
        #       ↓
        # RepositoryExecutionProfile
        #
        # The agent determines project type, framework, runner,
        # suite candidates and execution strategy.
        # ==========================================================

        repository_analysis_service = RepositoryAnalysisService(
            ai_service=ai_service,
            prompt_builder=prompt_builder,
        )

        repository_analysis_agent = RepositoryAnalysisAgent(
            repository_analysis_service=repository_analysis_service,
        )

        # ==========================================================
        # Approval
        # ==========================================================

        approval_service = InMemoryApprovalService()

        # ==========================================================
        # Repository workspace acquisition
        #
        # RepositorySource
        #       ↓
        # RepositoryResolver
        #       ↓
        # WorkspaceArtifact
        # ==========================================================

        workspace_service = LocalWorkspaceService()

        repository_materializer = GitRepositoryMaterializer()

        repository_resolver = RepositoryResolver(
            workspace_service=workspace_service,
            repository_materializer=repository_materializer,
        )

        repository_discovery = RepositoryDiscovery()

        # ==========================================================
        # Automation workspace materialization
        # ==========================================================

        automation_workspace_materializer = (
            AutomationWorkspaceMaterializer()
        )

        # ==========================================================
        # MCP repository operations
        #
        # Kept separate from workspace acquisition.
        # ==========================================================

        repository_provider = MCPRepositoryProvider(
            mcp_tool_executor=self.mcp_tool_executor,
            repository_agent=repository_execution_agent,
            approval_service=approval_service,
        )

        # ==========================================================
        # Capability registry
        # ==========================================================

        self.capability_registry = CapabilityRegistry(
            execution_server_resolver=execution_server_resolver,
            execution_provider_factory=execution_provider_factory,
            mcp_execution_agent=mcp_execution_agent,
            mcp_tool_executor=self.mcp_tool_executor,
            repository_provider=repository_provider,
            repository_resolver=repository_resolver,
            repository_discovery=repository_discovery,
            automation_workspace_materializer=(
                automation_workspace_materializer
            ),
            repository_analysis_agent=repository_analysis_agent,
        )

        # ==========================================================
        # Action catalog
        # ==========================================================

        action_catalog = ActionCatalog(
            tool_registry=tool_registry,
            capability_registry=self.capability_registry,
        )

        # ==========================================================
        # Agents
        # ==========================================================

        self.agent_registry = AgentRegistry(
            tool_registry,
            self.capability_registry,
            action_catalog,
            ai_service,
            prompt_builder,
            episode_service,
            repository_analysis_agent=repository_analysis_agent,
        )

        # ==========================================================
        # Workflow infrastructure
        # ==========================================================

        artifact_manager = ArtifactManager()

        node_registry = NodeRegistry(
            self.agent_registry,
            artifact_manager,
            episode_service,
            approval_service,
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
            workflow_manager,
            episode_service,
        )