from agents.base_agent import BaseAgent
from agents.mcp_execution_agent import MCPExecutionAgent
from agents.repository_analysis_agent import RepositoryAnalysisAgent
from agents.requirement_agent import RequirementAgent
from agents.planner_agent import PlannerAgent
from agents.execution_agent import ExecutionAgent
from agents.review_agent import ReviewAgent
from agents.requirement_intelligence_agent import RequirementIntelligenceAgent

from ai.builders.prompt_builder import PromptBuilder

from registries.base_registry import BaseRegistry

from services.mcp_execution_service import MCPExecutionService
from services.planning_service import PlanningService
from services.repository.repository_analysis_service import RepositoryAnalysisService
from services.requirement_intelligence_service import RequirementIntelligenceService
from services.review_service import ReviewService


class AgentRegistry(BaseRegistry[BaseAgent]):

    def __init__(
        self,
        tool_registry,
        capability_registry,
        action_catalog,
        ai_service,
        prompt_builder: PromptBuilder,
        episode_service,
        repository_analysis_agent
    ):
        super().__init__()

        self.tool_registry = tool_registry
        self.capability_registry = capability_registry
        self.action_catalog = action_catalog
        self.ai_service = ai_service
        self.prompt_builder = prompt_builder
        self.episode_service = episode_service
        self.repository_analysis_agent=repository_analysis_agent
        self._register_default_agents()

    def _register_default_agents(self):

        # Create services
        planning_service = PlanningService(
            self.ai_service,
            self.action_catalog.specs(),
            self.prompt_builder,
        )

        review_service = ReviewService(
            self.ai_service,
            self.prompt_builder,
        )

        intelligence_service = RequirementIntelligenceService(
            self.ai_service,
            self.prompt_builder,
        )

        mcp_execution_service = MCPExecutionService(
            self.ai_service,
            self.prompt_builder,
        )

        repository_analysis_service = RepositoryAnalysisService(self.ai_service,self.prompt_builder,)


        # Register agents
        self.register(
            "requirement",
            RequirementAgent(),
        )

        self.register(
            "planner",
            PlannerAgent(planning_service),
        )

        self.register(
            "execution",
            ExecutionAgent(
                self.tool_registry,
                self.capability_registry,
                self.episode_service,
            ),
        )

        self.register(
            "review",
            ReviewAgent(review_service),
        )

        self.register(
            "intelligence",
            RequirementIntelligenceAgent(
                intelligence_service,
            ),
        )

        self.register(
            "mcp_execution",
            MCPExecutionAgent(
                mcp_execution_service,
            ),
        )

        self.register(
            "repository_analysis",
            RepositoryAnalysisAgent(
                repository_analysis_service=(
                    repository_analysis_service
                ),
            ),
        )