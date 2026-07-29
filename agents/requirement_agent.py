from agents.base_agent import BaseAgent
from utils.logger import logger


class RequirementAgent(BaseAgent):

    def execute(self, state):
        logger.info(f"Requirement received: {state.requirement}")
        return state