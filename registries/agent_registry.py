from agents.base_agent import BaseAgent
from agents.requirement_agent import RequirementAgent
from agents.planner_agent import PlannerAgent
from agents.execution_agent import ExecutionAgent
from agents.review_agent import ReviewAgent
from agents.requirement_intelligence_agent import RequirementIntelligenceAgent
from ai.builders.prompt_builder import PromptBuilder
from registries.base_registry import BaseRegistry
from services.planning_service import PlanningService
from services.requirement_intelligence_service import RequirementIntelligenceService
from services.review_service import ReviewService


class AgentRegistry(BaseRegistry[BaseAgent]):

    def __init__(self, tool_registry, ai_service,prompt_builder:PromptBuilder,episode_service,):

        super().__init__()

        self.tool_registry = tool_registry
        self.ai_service = ai_service
        self.prompt_builder=prompt_builder
        self.episode_service = episode_service
        self.available_capabilities = (self.tool_registry.get_registered_names())
        self._register_default_agents()




    def _register_default_agents(self):

        # Create services
        planning_service = PlanningService(self.ai_service,self.available_capabilities, self.prompt_builder)
        review_service=ReviewService(self.ai_service, self.prompt_builder)
        intelligence_service = RequirementIntelligenceService(self.ai_service, self.prompt_builder)

        # Register agents
        self.register(
            "requirement",
            RequirementAgent()
        )

        self.register(
            "planner",
            PlannerAgent(planning_service)
        )

        self.register(
            "execution",
            ExecutionAgent(self.tool_registry,self.episode_service)
        )

        self.register(
            "review",
            ReviewAgent(review_service)
        )

        self.register(
            "intelligence",
            RequirementIntelligenceAgent(intelligence_service)
        )