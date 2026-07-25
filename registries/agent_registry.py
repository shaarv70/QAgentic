from agents.requirement_agent import RequirementAgent
from agents.planner_agent import PlannerAgent
from agents.execution_agent import ExecutionAgent
from agents.review_agent import ReviewAgent
from agents.requirement_intelligence_agent import RequirementIntelligenceAgent
from registries.base_registry import BaseRegistry
from services.planning_service import PlanningService
from services.requirement_service import RequirementService
from services.review_service import ReviewService


class AgentRegistry(BaseRegistry):

    def __init__(self, tool_registry, llm_service):

        super().__init__()

        self.tool_registry = tool_registry
        self.llm_service = llm_service
        self._register_default_agents()

    
    
    def _register_default_agents(self):

        # Create services
        planning_service = PlanningService(self.llm_service)
        requirement_service = RequirementService(self.llm_service)
        review_service=ReviewService(self.llm_service)

        # Register agents
        self.register(
            "requirement",
            RequirementAgent(requirement_service)
        )

        self.register(
            "planner",
            PlannerAgent(planning_service)
        )

        self.register(
            "execution",
            ExecutionAgent(self.tool_registry)
        )

        self.register(
            "review",
            ReviewAgent(review_service)
        )

        self.register(
            "intelligence",
            RequirementIntelligenceAgent()
        )