from agents.base_agent import BaseAgent
from utils.logger import logger


class RequirementIntelligenceAgent(BaseAgent):

    def __init__(self, intelligence_service):

        super().__init__()

        self.intelligence_service = intelligence_service


    def execute(self, state):

        intelligence = self.intelligence_service.analyze( state.requirement)

        state.requirement_intelligence = intelligence

        logger.info(
            f"Requirement Status: {intelligence.status}"
        )

        logger.info(
            f"Intent: {intelligence.intent}"
        )

        if intelligence.assumptions:

            logger.info(
                f"Assumptions: {intelligence.assumptions}"
            )

        return state