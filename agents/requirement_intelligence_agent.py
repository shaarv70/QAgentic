from agents.base_agent import BaseAgent
from utils.logger import logger


class RequirementIntelligenceAgent(BaseAgent):

    def __init__(self, intelligence_service):

        super().__init__()

        self.intelligence_service = intelligence_service


    def execute(self, state):

        clarification_context = (state.conversation.get_clarification_text() if state.conversation else "")

        intelligence = self.intelligence_service.analyze(state.requirement,clarification_context)

        state.requirement_intelligence = intelligence

        logger.info(f"Requirement Status: {intelligence.status}")

        logger.info(f"Intent: {intelligence.intent}")

        if intelligence.assumptions:

            logger.info(f"Assumptions: {intelligence.assumptions}")

        if getattr(intelligence, "unknowns", None):logger.info(f"Unknowns: {intelligence.unknowns}")

        return state